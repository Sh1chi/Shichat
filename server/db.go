package main

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/jackc/pgx/v5/pgxpool"
	"net"
	"os"
	"time"
)

// DB — глобальный пул соединений с базой PostgreSQL.
// Он создаётся при запуске сервера и используется всеми функциями.
var DB *pgxpool.Pool

// InitDB инициализирует подключение к базе данных.
// Использует строку подключения из переменной окружения DATABASE_URL,
// либо устанавливает значение по умолчанию.
// Проверяет соединение и сохраняет пул в глобальной переменной DB.
func InitDB() error {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		// Строка подключения по умолчанию
		dsn = "postgres://postgres:n52RO10AD150@localhost:5432/messenger_DB?sslmode=disable"
	}

	// Создаём контекст с таймаутом 5 секунд — если база не отвечает, ошибка
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// Подключаемся к базе
	var err error
	DB, err = pgxpool.New(ctx, dsn)
	if err != nil {
		return fmt.Errorf("не получилось создать пул: %w", err)
	}

	// Проверяем доступность базы
	if err = DB.Ping(ctx); err != nil {
		return fmt.Errorf("БД недоступна: %w", err)
	}

	fmt.Println("PostgreSQL подключена")
	return nil
}

// GetOrCreatePrivateChat возвращает ID приватного чата между двумя пользователями.
// Если такой чат уже есть, возвращает его ID. Иначе создаёт новый чат и добавляет участников.
func GetOrCreatePrivateChat(ctx context.Context, user1, user2 int64) (int64, error) {
	// Чтобы избежать дубликатов (user1 ↔ user2), сортируем ID по возрастанию
	if user1 > user2 {
		user1, user2 = user2, user1
	}

	// Ищем существующий чат, где оба пользователя являются участниками, и он не групповой
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
		// Чат найден — возвращаем его ID
		return chatID, nil
	}

	// Чата нет — создаём новый
	err = DB.QueryRow(ctx, `INSERT INTO chats (is_group) VALUES (false) RETURNING id`).Scan(&chatID)
	if err != nil {
		return 0, err
	}

	// Добавляем обоих пользователей в chat_members
	_, err = DB.Exec(ctx, `
		INSERT INTO chat_members (chat_id, user_id)
		VALUES ($1, $2), ($1, $3)
	`, chatID, user1, user2)
	if err != nil {
		return 0, err
	}

	return chatID, nil
}

// fetchUserChats возвращает список чатов пользователя с краткой информацией:
// ID чата, имя собеседника или название группы, последнее сообщение и время.
func fetchUserChats(ctx context.Context, uid int64) ([]ChatPreview, error) {
	const q = `
	SELECT
	  ch.id AS chat_id,
	  CASE
		WHEN ch.is_group
			 THEN ch.id::TEXT          -- для групп возвращаем ID как строку
		ELSE u2.username               -- для приватных — логин собеседника
	  END AS peer,
	  CASE
		WHEN ch.is_group
			 THEN ch.title
		ELSE u2.display_name
	  END AS display_name,
	  COALESCE(m.content, '') AS last_msg,
	  COALESCE(EXTRACT(EPOCH FROM m.sent_at), 0)::BIGINT AS last_ts
	FROM chats ch
	JOIN chat_members cm ON cm.chat_id = ch.id AND cm.user_id = $1
	LEFT JOIN LATERAL (
	  SELECT content, sent_at
	  FROM messages
	  WHERE chat_id = ch.id
	  ORDER BY sent_at DESC
	  LIMIT 1
	) m ON true
	LEFT JOIN LATERAL (
	  SELECT u.username, u.display_name
	  FROM chat_members cm2
	  JOIN users u ON u.id = cm2.user_id
	  WHERE cm2.chat_id = ch.id
		AND ch.is_group = false
		AND cm2.user_id <> $1
	  LIMIT 1
	) u2 ON true
	ORDER BY last_ts DESC;
	`

	// Выполняем SQL-запрос
	rows, err := DB.Query(ctx, q, uid)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	// Сканируем строки в слайс ChatPreview
	var out []ChatPreview
	for rows.Next() {
		var c ChatPreview
		if err := rows.Scan(
			&c.ChatID,
			&c.Peer,
			&c.DisplayName,
			&c.LastMsg,
			&c.LastTS,
		); err != nil {
			return nil, err
		}
		out = append(out, c)
	}
	return out, nil
}

// sendChatList отправляет клиенту список чатов в виде JSON.
// Используется после входа, создания чата или группы.
func sendChatList(conn net.Conn, uid int64) {
	chats, err := fetchUserChats(context.Background(), uid)
	if err != nil {
		// Ошибку можно логгировать, но клиенту не отправляем
		//return
	}

	// Формируем JSON-пакет и отправляем по соединению
	msg := Message{Type: "chatlist", Chats: chats}
	data, _ := json.Marshal(msg)
	conn.Write(append(data, '\n'))
}
