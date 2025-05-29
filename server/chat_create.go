package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
)

// handleStartChat обрабатывает запрос на создание приватного чата.
// Получает ID собеседника, создаёт (или находит) чат в базе и отправляет клиенту информацию о чате.
func handleStartChat(conn net.Conn, m Message) {
	ctx := context.Background()
	sender := clients[conn]
	if sender == nil {
		// Соединение не зарегистрировано как клиент — игнорируем
		return
	}

	// Получаем ID пользователя, с которым нужно начать чат
	var peerID int64
	err := DB.QueryRow(ctx, `SELECT id FROM users WHERE username=$1`, m.To).Scan(&peerID)
	if err != nil {
		fmt.Println("Ошибка БД (поиск собеседника):", err)
		return
	}

	// Создаём новый чат или получаем ID уже существующего
	chatID, err := GetOrCreatePrivateChat(ctx, sender.ID, peerID)
	if err != nil {
		fmt.Println("Ошибка БД (создание чата):", err)
		return
	}

	// Формируем краткое описание нового чата для клиента
	preview := ChatPreview{
		ChatID:      chatID,
		Peer:        m.To,
		DisplayName: m.To, // Можно улучшить: взять имя+фамилию из БД
		LastMsg:     "",
		LastTS:      0,
	}

	// Отправляем клиенту информацию о созданном чате
	resp := Message{Type: "chat_created", Chat: &preview}
	data, _ := json.Marshal(resp)
	conn.Write(append(data, '\n'))

	// Обновляем клиенту список чатов
	sendChatList(conn, sender.ID)
}

// handleCreateGroup обрабатывает создание группового чата.
// Создаёт запись в таблице чатов, добавляет участников и уведомляет всех онлайн-юзеров.
func handleCreateGroup(conn net.Conn, m Message) {
	// Получаем информацию о создателе чата
	mu.Lock()
	sender := clients[conn]
	mu.Unlock()
	if sender == nil {
		return
	}

	ctx := context.Background()

	// Формируем список участников: все из сообщения + сам создатель
	members := append(m.Participants, sender.Name)

	// Удаляем дубликаты имён (на всякий случай)
	uniq := make(map[string]struct{})
	var usersList []string
	for _, u := range members {
		if _, seen := uniq[u]; !seen {
			uniq[u] = struct{}{}
			usersList = append(usersList, u)
		}
	}

	// Получаем user_id по username для всех участников
	var userIDs []int64
	for _, uname := range usersList {
		var uid int64
		if err := DB.QueryRow(ctx,
			`SELECT id FROM users WHERE username=$1`, uname,
		).Scan(&uid); err != nil {
			sendError(conn, fmt.Sprintf("Пользователь %s не найден", uname))
			return
		}
		userIDs = append(userIDs, uid)
	}

	// Создаём новый групповой чат в базе данных
	var chatID int64
	err := DB.QueryRow(ctx,
		`INSERT INTO chats(is_group, title, creator_id)
         VALUES (true, $1, $2)
         RETURNING id`,
		m.Name, sender.ID,
	).Scan(&chatID)
	if err != nil {
		fmt.Println("Ошибка БД (добавление участника в группу):", err)
		return
	}

	// Добавляем каждого участника в таблицу chat_members
	for _, uid := range userIDs {
		if _, err := DB.Exec(ctx,
			`INSERT INTO chat_members(chat_id, user_id) VALUES($1,$2)`,
			chatID, uid,
		); err != nil {
			fmt.Println("Ошибка БД (добавление участника в группу):", err)
			return
		}
	}

	// Отправляем клиенту информацию о новой группе
	preview := ChatPreview{
		ChatID:      chatID,
		Peer:        fmt.Sprint(chatID), // для группы peer — это строка с ID
		DisplayName: m.Name,
		LastMsg:     "",
		LastTS:      0,
	}
	resp := Message{Type: "group_created", Chat: &preview}
	data, _ := json.Marshal(resp)
	conn.Write(append(data, '\n'))

	// Всем онлайн-участникам отправляем обновлённый список чатов
	for _, uid := range userIDs {
		mu.Lock()
		for c, cl := range clients {
			if cl.ID == uid {
				sendChatList(c, uid)
			}
		}
		mu.Unlock()
	}
}
