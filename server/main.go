package main

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"net"
	"sync"
	"time"
)

// Структура описывает формат всех сообщений между клиентом и сервером.
// Тип определяет, о чём это сообщение: регистрация, личное сообщение или список пользователей.
type Message struct {
	Type      string        `json:"type"`              // Тип сообщения: "signup", "signin", "message", "history" "userlist"
	From      string        `json:"from,omitempty"`    // Имя отправителя
	To        string        `json:"to,omitempty"`      // Имя получателя (для личных сообщений)
	Content   string        `json:"content,omitempty"` // Содержимое сообщения
	Password  string        `json:"password,omitempty"`
	FirstName string        `json:"first_name,omitempty"`
	LastName  string        `json:"last_name,omitempty"`
	Query     string        `json:"query,omitempty"`
	Timestamp int64         `json:"timestamp,omitempty"` // Метка времени (секунды Unix)
	Chats     []ChatPreview `json:"chats,omitempty"`
	Users     []UserSummary `json:"users,omitempty"`
	Chat      *ChatPreview  `json:"chat,omitempty"`
}

type ChatPreview struct {
	ChatID      int64  `json:"chat_id"`
	Peer        string `json:"peer"` // username собеседника
	DisplayName string `json:"display_name"`
	LastMsg     string `json:"last_msg"`
	LastTS      int64  `json:"last_ts"`
}

// Новые структуры для выдачи результатов поиска
// Пользователь для поиска
type UserSummary struct {
	Username    string `json:"username"`
	DisplayName string `json:"display_name"`
}

// Структура клиента: имя и соединение.
type Client struct {
	Conn net.Conn
	Name string
	ID   int64
}

// Глобальные переменные для хранения подключённых клиентов
var (
	clients    = make(map[net.Conn]*Client) // карта: соединение → клиент
	nameToConn = make(map[string]net.Conn)  // карта: имя → соединение
	mu         sync.Mutex                   // мьютекс для защиты общих карт от одновременного доступа
)

func main() {
	if err := InitDB(); err != nil {
		panic(err)
	}
	defer DB.Close()

	// Запускаем TCP-сервер на порту 8080
	ln, err := net.Listen("tcp", ":8080")
	if err != nil {
		panic(err)
	}
	defer ln.Close()
	fmt.Println("Server is listening on :8080")

	for {
		// Принимаем новое входящее соединение
		conn, err := ln.Accept()
		if err != nil {
			continue
		}
		// Для каждого клиента запускаем отдельную горутину
		go handleConnection(conn)
	}
}

// Обрабатывает одно клиентское соединение: сначала регистрация, затем приём сообщений.
func handleConnection(conn net.Conn) {
	defer func() {
		removeClient(conn) // Удаляем клиента при отключении
		conn.Close()
	}()

	scanner := bufio.NewScanner(conn)

	// Увеличиваем допустимый размер сообщения до 1 МБ
	buf := make([]byte, 0, 64*1024)
	scanner.Buffer(buf, 1024*1024)

	// Ждём первое сообщение от клиента — оно должно быть регистрационным
	if !scanner.Scan() {
		return
	}

	var initMsg Message
	if err := json.Unmarshal(scanner.Bytes(), &initMsg); err != nil {
		return
	}

	switch initMsg.Type {
	case "signup":
		handleSignup(conn, initMsg)
		return // после успешной регистрации можно закрыть соединение
	case "signin":
		// Проверяем пароль, обновляем last_login_at и шлём login_ok
		userID, err := handleLogin(conn, initMsg)
		if err != nil {
			// При ошибке handleLogin сам отправит sendError и мы просто выходим
			return
		}

		// Регистрация в оперативных структурах — без return!
		mu.Lock()
		// если уже онлайн — убираем старое
		if old, ok := nameToConn[initMsg.From]; ok {
			old.Close()
			delete(clients, old)
		}
		clients[conn] = &Client{Conn: conn, Name: initMsg.From, ID: userID}
		nameToConn[initMsg.From] = conn
		mu.Unlock()

	default:
		// ни signup, ни signin — обрываем
		return
	}

	// Цикл приёма всех последующих сообщений от клиента
	for scanner.Scan() {
		var m Message
		if err := json.Unmarshal(scanner.Bytes(), &m); err != nil {
			continue // если пришёл мусор — пропускаем
		}
		switch m.Type {
		case "message":
			handlePersonalMessage(conn, m) // обрабатываем личное сообщение
		case "history":
			handleHistoryRequest(conn, m)
		case "user_search":
			go handleUserSearch(conn, m)
		case "start_chat":
			go handleStartChat(conn, m)
		default:
			// Неизвестный тип пакета — игнорируем
		}
	}
}

// Обрабатывает личное сообщение:
// 1) сохраняет в БД,
// 2) шлёт получателю и самому отправителю,
// 3) обновляет у них список чатов (превью последнего сообщения).
func handlePersonalMessage(senderConn net.Conn, m Message) {
	mu.Lock()
	receiverConn, ok := nameToConn[m.To] // находим коннект получателя
	sender := clients[senderConn]        // данные отправителя
	mu.Unlock()

	if sender == nil {
		return // получателя нет — просто выходим
	}

	// Если таймстамп не пришёл — ставим текущее время
	if m.Timestamp == 0 {
		m.Timestamp = time.Now().Unix()
	}
	// На всякий случай подставляем имя отправителя
	m.From = sender.Name

	ctx := context.Background()

	var receiverID int64
	err := DB.QueryRow(ctx,
		`SELECT id FROM users WHERE username=$1`, m.To,
	).Scan(&receiverID)
	if err != nil {
		// такого пользователя нет в БД — можно отправить ошибку или просто вернуть
		sendError(senderConn, "Пользователь не найден")
		return
	}

	// Получаем или создаём приватный чат
	chatID, err := GetOrCreatePrivateChat(ctx, sender.ID, receiverID)
	if err != nil {
		fmt.Println("DB error (chat):", err)
		return
	}
	// Сохраняем сообщение
	if err := SavePrivateMessage(ctx, chatID, sender.ID, m.Content); err != nil {
		fmt.Println("Ошибка сохранения сообщения:", err)
	}

	// Сериализуем пакет для отправки
	data, _ := json.Marshal(m)
	data = append(data, '\n')

	// 1) Эхо отправителю — всегда
	senderConn.Write(data)
	// 2) Если получатель сейчас онлайн — шлём ему тоже
	if ok && receiverConn != senderConn {
		receiverConn.Write(data)
	}

	// 1) всегда обновляем отправителю
	sendChatList(senderConn, sender.ID)
	// 2) а получателю — только если он онлайн
	if ok {
		sendChatList(receiverConn, receiverID)
	}
}

/*
// Рассылает всем клиентам список имён пользователей, которые сейчас онлайн
func broadcastUserList() {
	mu.Lock()
	usernames := make([]string, 0, len(nameToConn))
	for name := range nameToConn {
		usernames = append(usernames, name)
	}
	conns := make([]net.Conn, 0, len(clients))
	for c := range clients {
		conns = append(conns, c)
	}
	mu.Unlock()

	pkt := Message{
		Type:  "userlist",
		Users: usernames,
	}
	data, _ := json.Marshal(pkt)
	data = append(data, '\n')

	for _, c := range conns {
		c.Write(data)
	}
}
*/

// Удаляет клиента из общих структур при отключении
func removeClient(conn net.Conn) {
	mu.Lock()
	if cl, ok := clients[conn]; ok {
		delete(nameToConn, cl.Name) // удаляем по имени
	}
	delete(clients, conn) // удаляем по соединению
	mu.Unlock()

}
