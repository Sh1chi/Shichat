package main

import (
	"context"
	"encoding/json"
	"fmt"
	"golang.org/x/crypto/bcrypt"
	"net"
	"strings"
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
	// 1) Снимаем sender из clients под мьютексом
	mu.Lock()
	sender := clients[conn]
	mu.Unlock()
	if sender == nil {
		return // неавторизованный
	}

	ctx := context.Background()

	// 2) Узнаём ID собеседника из БД (peer = m.To)
	var receiverID int64
	if err := DB.QueryRow(ctx,
		`SELECT id FROM users WHERE username = $1`, m.To,
	).Scan(&receiverID); err != nil {
		fmt.Println("DB error (lookup receiver):", err)
		return
	}

	// 3) Получаем или создаём chat_id для этой пары
	chatID, err := GetOrCreatePrivateChat(ctx, sender.ID, receiverID)
	if err != nil {
		fmt.Println("DB error (chat):", err)
		return
	}

	// 4) Достаем последние 50 сообщений (DESC → самые свежие первыми)
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

	// 5) Собираем []Message в порядке старые→новые
	var history []Message
	for rows.Next() {
		var senderID int64
		var content string
		var ts time.Time
		if err := rows.Scan(&senderID, &content, &ts); err != nil {
			continue
		}
		// определяем from/to
		var fromUser, toUser string
		if senderID == sender.ID {
			fromUser = sender.Name
			toUser = m.To
		} else {
			fromUser = m.To
			toUser = sender.Name
		}
		// prepend, чтобы oldest→newest
		history = append([]Message{{
			Type:      "message",
			From:      fromUser,
			To:        toUser,
			Content:   content,
			Timestamp: ts.Unix(),
		}}, history...)
	}

	// 6) Шлём клиенту каждое сообщение в JSON-строке
	for _, msg := range history {
		data, _ := json.Marshal(msg)
		conn.Write(append(data, '\n'))
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

	sendChatList(conn, userID)
	return userID, nil
}

func fetchUserChats(ctx context.Context, uid int64) ([]ChatPreview, error) {
	const q = `
      SELECT ch.id, u.username, u.display_name,
             COALESCE(m.content, '') AS last_msg,
             COALESCE(EXTRACT(EPOCH FROM m.sent_at),0)::BIGINT AS last_ts
      FROM chats ch
      JOIN chat_members cm ON cm.chat_id=ch.id AND cm.user_id=$1
      JOIN chat_members cm2 ON cm2.chat_id=ch.id AND cm2.user_id<>$1
      JOIN users u ON u.id=cm2.user_id
      LEFT JOIN LATERAL (
        SELECT content, sent_at
        FROM messages
        WHERE chat_id=ch.id
        ORDER BY sent_at DESC
        LIMIT 1
      ) m ON true;
    `
	rows, err := DB.Query(ctx, q, uid)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var out []ChatPreview
	for rows.Next() {
		var c ChatPreview
		if err := rows.Scan(&c.ChatID, &c.Peer, &c.DisplayName, &c.LastMsg, &c.LastTS); err != nil {
			return nil, err
		}
		out = append(out, c)
	}
	return out, nil
}

func sendChatList(conn net.Conn, uid int64) {
	chats, err := fetchUserChats(context.Background(), uid)
	if err != nil { /* логгировать и return */
	}
	msg := Message{Type: "chatlist", Chats: chats}
	data, _ := json.Marshal(msg)
	conn.Write(append(data, '\n'))
}

// ===== Реализация handleUserSearch =====
func handleUserSearch(conn net.Conn, m Message) {
	q := strings.TrimSpace(m.Query) // теперь берём именно поле query
	if q == "" {
		return
	}
	ctx := context.Background()
	rows, err := DB.Query(ctx, `
        SELECT username, display_name
        FROM users
        WHERE username ILIKE $1 OR display_name ILIKE $1
        ORDER BY username
        LIMIT 20
    `, "%"+q+"%")
	if err != nil {
		fmt.Println("DB error (user search):", err)
		return
	}
	defer rows.Close()

	var results []UserSummary
	for rows.Next() {
		var u UserSummary
		rows.Scan(&u.Username, &u.DisplayName)
		results = append(results, u)
	}
	// отпавляем клиенту список
	resp := Message{Type: "user_search_result", Users: results}
	data, _ := json.Marshal(resp)
	conn.Write(append(data, '\n'))
}

// ===== Реализация handleStartChat =====
func handleStartChat(conn net.Conn, m Message) {
	// Предполагаем, что поле m.Peer передано в m.To
	ctx := context.Background()
	sender := clients[conn]
	if sender == nil {
		return
	}
	// получаем ID получателя
	var peerID int64
	err := DB.QueryRow(ctx, `SELECT id FROM users WHERE username=$1`, m.To).Scan(&peerID)
	if err != nil {
		fmt.Println("DB error (lookup peer):", err)
		return
	}
	// создаём или получаем чат
	chatID, err := GetOrCreatePrivateChat(ctx, sender.ID, peerID)
	if err != nil {
		fmt.Println("DB error (start chat):", err)
		return
	}
	// собираем превью для нового чата (без last_msg)
	preview := ChatPreview{
		ChatID:      chatID,
		Peer:        m.To,
		DisplayName: m.To, // можно взять из users.display_name, если нужно
		LastMsg:     "",
		LastTS:      0,
	}
	// отправляем клиенту
	resp := Message{Type: "chat_created", Chat: &preview}
	data, _ := json.Marshal(resp)
	conn.Write(append(data, '\n'))
	// обновляем список у отправителя
	sendChatList(conn, sender.ID)
}
