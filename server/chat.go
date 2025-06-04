package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"strconv"
	"time"
)

// handleMessage обрабатывает входящее сообщение от клиента.
// Определяет тип чата (приватный или групповой), сохраняет сообщение,
// рассылает его другим участникам и обновляет списки чатов.
func handleMessage(senderConn net.Conn, m Message) {
	// Получаем объект клиента, который отправил сообщение
	mu.Lock()
	sender := clients[senderConn]
	mu.Unlock()
	if sender == nil {
		return // если клиент не найден — выходим
	}

	ctx := context.Background()

	// Если это не группа — значит, приватный чат, нужно получить chatID вручную
	var chatID int64
	if id, err := strconv.ParseInt(m.To, 10, 64); err == nil {
		chatID = id // это групповой чат
	} else {
		// Получаем ID получателя и создаём приватный чат при необходимости
		var recvID int64
		if err := DB.QueryRow(ctx,
			`SELECT id FROM users WHERE username=$1`, m.To,
		).Scan(&recvID); err != nil {
			sendError(senderConn, "Пользователь не найден")
			return
		}
		var err2 error
		chatID, err2 = GetOrCreatePrivateChat(ctx, sender.ID, recvID)
		if err2 != nil {
			fmt.Println("Ошибка БД (поиск или создание чата):", err2)
			return
		}
	}

	// Заполняем служебные поля сообщения
	if m.Timestamp == 0 {
		m.Timestamp = time.Now().Unix()
	}
	m.From = sender.Name
	_ = DB.QueryRow(ctx,
		`SELECT display_name FROM users WHERE id=$1`, sender.ID,
	).Scan(&m.DisplayName)

	// Сохраняем сообщение в базу данных
	if _, err := DB.Exec(ctx,
		`INSERT INTO messages(chat_id, sender_id, content)
		 VALUES ($1,$2,$3)`,
		chatID, sender.ID, m.Content,
	); err != nil {
		fmt.Println("Ошибка БД (сохранение сообщения):", err)
		return
	}

	// Отправляем сообщение обратно отправителю (эхо)
	data, _ := json.Marshal(m)
	data = append(data, '\n')
	senderConn.Write(data)

	// Рассылаем сообщение другим участникам
	if _, err := strconv.ParseInt(m.To, 10, 64); err == nil {
		// Групповой чат — получаем всех участников
		rows, _ := DB.Query(ctx,
			`SELECT user_id FROM chat_members WHERE chat_id=$1`, chatID)
		defer rows.Close()
		for rows.Next() {
			var uid int64
			rows.Scan(&uid)
			if uid == sender.ID {
				continue // не отправляем самому себе
			}
			mu.Lock()
			for c, cl := range clients {
				if cl.ID == uid {
					c.Write(data)
				}
			}
			mu.Unlock()
		}
	} else {
		// Приватный чат — отправляем второму участнику
		mu.Lock()
		if rc, ok := nameToConn[m.To]; ok && rc != senderConn {
			rc.Write(data)
		}
		mu.Unlock()
	}

	// Обновляем список чатов у отправителя
	sendChatList(senderConn, sender.ID)

	// Также обновляем чат-листы у остальных участников
	if _, err := strconv.ParseInt(m.To, 10, 64); err == nil {
		rows, _ := DB.Query(ctx,
			`SELECT user_id FROM chat_members WHERE chat_id=$1`, chatID)
		defer rows.Close()
		for rows.Next() {
			var uid int64
			rows.Scan(&uid)
			mu.Lock()
			for c, cl := range clients {
				if cl.ID == uid {
					sendChatList(c, uid)
				}
			}
			mu.Unlock()
		}
	} else {
		// Приватный чат — обновляем только у собеседника
		mu.Lock()
		if rc, ok := nameToConn[m.To]; ok {
			recipientID := clients[rc].ID
			sendChatList(rc, recipientID)
		}
		mu.Unlock()
	}
}

// handleHistoryRequest обрабатывает запрос истории сообщений в чате.
// Возвращает клиенту 50 последних сообщений в нужном порядке.
func handleHistoryRequest(conn net.Conn, m Message) {
	// Получаем отправителя по соединению
	mu.Lock()
	sender := clients[conn]
	mu.Unlock()
	if sender == nil {
		return
	}
	ctx := context.Background()

	var chatID int64
	// Если это приватный чат — находим или создаём его
	if id, err := strconv.ParseInt(m.To, 10, 64); err == nil {
		chatID = id
	} else {
		var rid int64
		if err := DB.QueryRow(ctx,
			`SELECT id FROM users WHERE username=$1`, m.To,
		).Scan(&rid); err != nil {
			return
		}
		chatID, _ = GetOrCreatePrivateChat(ctx, sender.ID, rid)
	}

	// Запрашиваем 50 последних сообщений
	rows, err := DB.Query(ctx, `
		SELECT m.sender_id, u.username, u.display_name, m.content, m.sent_at
		FROM messages m
		JOIN users u ON u.id = m.sender_id
		WHERE m.chat_id=$1
		ORDER BY m.sent_at DESC
		LIMIT 50`, chatID)
	if err != nil {
		return
	}
	defer rows.Close()

	var history []Message

	// Читаем каждое сообщение из результата
	for rows.Next() {
		var sid int64
		var username, dname, content string
		var ts time.Time
		if err := rows.Scan(&sid, &username, &dname, &content, &ts); err != nil {
			continue
		}

		// Формируем структуру Message и добавляем в начало списка
		from, to := username, m.To
		if sid == sender.ID {
			from = sender.Name
		}
		history = append([]Message{{
			Type:        "message",
			From:        from,
			To:          to,
			Content:     content,
			DisplayName: dname,
			Timestamp:   ts.Unix(),
		}}, history...)
	}

	// Отправляем клиенту каждое сообщение по одному
	for _, msg := range history {
		data, _ := json.Marshal(msg)
		conn.Write(append(data, '\n'))
	}
}
