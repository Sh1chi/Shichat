package main

import (
	"context"
	"encoding/json"
	"fmt"
	"golang.org/x/crypto/bcrypt"
	"net"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"os"
)

/*
======== Глобальные переменные ========
DB — пул соединений с Postgres, им пользуются все функции.
*/
var DB *pgxpool.Pool

// InitDB открывает пул соединений к базе данных.
//   - Берёт DSN из переменной окружения DATABASE_URL (или ставит дефолт).
//   - Пытается установить соединение и «пингует» базу,
//     чтобы сразу узнать о проблемах сети/доступа.
//   - Если всё ок — сохраняет пул в глобальной переменной DB.
func InitDB() error {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		dsn = "postgres://postgres:n52RO10AD150@localhost:5432/messenger_DB?sslmode=disable"
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var err error
	DB, err = pgxpool.New(ctx, dsn)
	if err != nil {
		return fmt.Errorf("не получилось создать пул: %w", err)
	}

	if err = DB.Ping(ctx); err != nil {
		return fmt.Errorf("БД недоступна: %w", err)
	}

	fmt.Println("PostgreSQL подключена")
	return nil
}

/*
   ======== Работа с пользователями и чатами ========
*/

// GetOrCreateUser возвращает id пользователя по username.
// Если такого пользователя нет, он создаётся «по-быстрому» с заполнением
// только обязательных полей (пароль-заглушка 'not_used').
func GetOrCreateUser(ctx context.Context, username string) (int64, error) {
	var id int64
	query := `
		INSERT INTO users (username, first_name, password_hash)
		VALUES ($1, $1, 'not_used')
		ON CONFLICT (username) DO UPDATE
		SET last_login_at = CURRENT_TIMESTAMP
		RETURNING id
	`
	err := DB.QueryRow(ctx, query, username).Scan(&id)
	return id, err
}

// GetOrCreatePrivateChat ищет приватный чат между двумя user_id.
// Если он уже существует — возвращает его id.
// Иначе создаёт новый чат и добавляет в него обоих участников.
func GetOrCreatePrivateChat(ctx context.Context, user1, user2 int64) (int64, error) {
	// Чтобы сравнение пар (user1,user2) было детерминированным,
	// сортируем id по возрастанию
	if user1 > user2 {
		user1, user2 = user2, user1
	}

	// 1. Надёжно ищем существующий приватный чат между двумя пользователями
	var chatID int64
	query := `
	SELECT cm1.chat_id
	FROM chat_members cm1
	JOIN chat_members cm2 ON cm1.chat_id = cm2.chat_id
	JOIN chats c ON c.id = cm1.chat_id
	WHERE cm1.user_id = $1 AND cm2.user_id = $2 AND c.is_group = false
	LIMIT 1;
	`

	err := DB.QueryRow(ctx, query, user1, user2).Scan(&chatID)
	if err == nil {
		return chatID, nil // Нашли — возвращаем
	}

	// 2. Не нашли — создаём новый чат
	err = DB.QueryRow(ctx, `INSERT INTO chats (is_group) VALUES (false) RETURNING id`).Scan(&chatID)
	if err != nil {
		return 0, err
	}

	// Добавляем обеих пользователей как участников
	_, err = DB.Exec(ctx, `
		INSERT INTO chat_members (chat_id, user_id)
		VALUES ($1, $2), ($1, $3)
	`, chatID, user1, user2)
	if err != nil {
		return 0, err
	}

	return chatID, nil
}

// SavePrivateMessage сохраняет текстовое сообщение в БД.
func SavePrivateMessage(ctx context.Context, chatID, senderID int64, content string) error {
	_, err := DB.Exec(ctx, `
		INSERT INTO messages (chat_id, sender_id, content)
		VALUES ($1, $2, $3)
	`, chatID, senderID, content)
	return err
}

/*
   ======== Обработчики сетевых пакетов ========
*/

// handleHistoryRequest — ответ на запрос истории сообщений.
// Отправляет клиенту последние 50 сообщений диалога
// между текущим пользователем (conn) и m.To.
func handleHistoryRequest(conn net.Conn, m Message) {
	mu.Lock()
	sender := clients[conn] // кто спрашивает историю
	receiverConn, ok := nameToConn[m.To]
	receiver := clients[receiverConn] // с кем диалог
	mu.Unlock()

	// Если не нашли адресата — выходим тихо
	if sender == nil || !ok || receiver == nil {
		return
	}

	ctx := context.Background()

	// Находим (или создаём) приватный чат
	chatID, err := GetOrCreatePrivateChat(ctx, sender.ID, receiver.ID)
	if err != nil {
		fmt.Println("DB error (history chat):", err)
		return
	}

	// Берём последние 50 сообщений, самые свежие сверху
	rows, err := DB.Query(ctx, `
		SELECT sender_id, content, sent_at
		FROM messages
		WHERE chat_id = $1
		ORDER BY sent_at DESC
		LIMIT 50
	`, chatID)
	if err != nil {
		fmt.Println("DB error (history query):", err)
		return
	}
	defer rows.Close()

	// Собираем слайс Message в хронологическом порядке (старые → новые)
	var history []Message
	for rows.Next() {
		var senderID int64
		var content string
		var ts time.Time
		err := rows.Scan(&senderID, &content, &ts)
		if err != nil {
			continue
		}

		from := sender.Name
		to := receiver.Name
		if senderID == receiver.ID { // «кто отправил» меняем местами
			from = receiver.Name
			to = sender.Name
		}

		// Добавляем в начало (prepend), чтобы итоговый список был ↑ по времени
		history = append([]Message{{
			Type:      "message",
			From:      from,
			To:        to,
			Content:   content,
			Timestamp: ts.Unix(),
		}}, history...) // prepend — в правильном порядке
	}

	// Отправляем каждый message-пакет по очереди
	for _, msg := range history {
		data, _ := json.Marshal(msg)
		data = append(data, '\n')
		conn.Write(data)
	}
}

// handleSignup обрабатывает регистрацию нового пользователя.
func handleSignup(conn net.Conn, m Message) {
	// 1) Базовая валидация
	if m.From == "" || m.Password == "" || m.FirstName == "" {
		sendError(conn, "Логин, имя и пароль обязательны")
		return
	}
	username := m.From
	pwd := m.Password
	first := m.FirstName
	last := m.LastName // может быть пустым

	// 2) Проверяем, нет ли уже такого логина
	var exists bool
	err := DB.QueryRow(context.Background(),
		`SELECT EXISTS(SELECT 1 FROM users WHERE username=$1)`, username,
	).Scan(&exists)
	if err != nil {
		sendError(conn, "Ошибка проверки имени")
		return
	}
	if exists {
		sendError(conn, "Имя занято")
		return
	}

	// 3) Генерируем bcrypt-хэш
	hashBytes, err := bcrypt.GenerateFromPassword([]byte(pwd), bcrypt.DefaultCost)
	if err != nil {
		sendError(conn, "Ошибка хеширования пароля")
		return
	}
	hashed := string(hashBytes)

	// 4) Сохраняем пользователя в БД
	//    Пока plain-текст, но потом замените на bcrypt
	_, err = DB.Exec(context.Background(), `
        INSERT INTO users (username, first_name, last_name, password_hash)
        VALUES ($1, $2, $3, $4)
    `, username, first, last, hashed)
	if err != nil {
		sendError(conn, "Ошибка сохранения")
		return
	}

	// 5) Говорим клиенту «ОК»
	resp := Message{Type: "signup_ok", Content: "Регистрация прошла успешно"}
	data, _ := json.Marshal(resp)
	conn.Write(append(data, '\n'))
}

func sendError(conn net.Conn, text string) {
	resp := Message{
		Type:    "error",
		Content: text,
	}
	data, _ := json.Marshal(resp)
	conn.Write(append(data, '\n'))
}

func handleLogin(conn net.Conn, m Message) (userID int64, err error) {
	username := m.From
	pwd := m.Password

	// 1) Получаем запись из БД
	var hashInDB string
	err = DB.QueryRow(context.Background(),
		`SELECT id, password_hash FROM users WHERE username = $1`, username,
	).Scan(&userID, &hashInDB)
	if err != nil {
		sendError(conn, "Пользователь не найден")
		return 0, err
	}

	// 2) Простейшая проверка «plain:…»
	if err := bcrypt.CompareHashAndPassword([]byte(hashInDB), []byte(pwd)); err != nil {
		sendError(conn, "Неверный пароль")
		return 0, fmt.Errorf("auth failed")
	}

	// 3) Обновляем last_login_at
	if _, err := DB.Exec(context.Background(),
		`UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = $1`,
		userID,
	); err != nil {
		// Это не фейлит вход, просто логируем
		fmt.Println("DB warning: не удалось обновить last_login_at:", err)
	}

	// 4) Шлём клиенту подтверждение успешного входа
	resp := Message{Type: "login_ok", Content: "OK"}
	data, _ := json.Marshal(resp)
	conn.Write(append(data, '\n'))
	return userID, nil
}
