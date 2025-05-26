package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"net"
	"sync"
	"time"
)

// Структура описывает формат всех сообщений между клиентом и сервером.
// Тип определяет, о чём это сообщение: регистрация, личное сообщение или список пользователей.
type Message struct {
	Type      string   `json:"type"`                // Тип сообщения: "register", "message", "userlist"
	From      string   `json:"from,omitempty"`      // Имя отправителя
	To        string   `json:"to,omitempty"`        // Имя получателя (для личных сообщений)
	Content   string   `json:"content,omitempty"`   // Содержимое сообщения
	Timestamp int64    `json:"timestamp,omitempty"` // Метка времени (секунды Unix)
	Users     []string `json:"users,omitempty"`     // Список имён (используется в userlist)
}

// Структура клиента: имя и соединение.
type Client struct {
	Conn net.Conn
	Name string
}

// Глобальные переменные для хранения подключённых клиентов
var (
	clients    = make(map[net.Conn]*Client) // карта: соединение → клиент
	nameToConn = make(map[string]net.Conn)  // карта: имя → соединение
	mu         sync.Mutex                   // мьютекс для защиты общих карт от одновременного доступа
)

func main() {
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
	var reg Message
	if err := json.Unmarshal(scanner.Bytes(), &reg); err != nil || reg.Type != "register" || reg.From == "" {
		return // если пакет неправильный — отключаем клиента
	}
	username := reg.From

	mu.Lock()
	// Если пользователь с таким именем уже онлайн — отключаем его старое соединение
	if oldConn, exists := nameToConn[username]; exists {
		oldConn.Close()
		delete(clients, oldConn)
	}
	// Регистрируем нового клиента
	clients[conn] = &Client{Conn: conn, Name: username}
	nameToConn[username] = conn
	mu.Unlock()

	broadcastUserList() // Обновляем список пользователей у всех клиентов

	// Цикл приёма всех последующих сообщений от клиента
	for scanner.Scan() {
		var m Message
		if err := json.Unmarshal(scanner.Bytes(), &m); err != nil {
			continue // если пришёл мусор — пропускаем
		}
		switch m.Type {
		case "message":
			handlePersonalMessage(conn, m) // обрабатываем личное сообщение
		default:
			// Неизвестный тип пакета — игнорируем
		}
	}
}

// Обрабатывает личное сообщение: отправляет его получателю и самому отправителю (эхо).
func handlePersonalMessage(senderConn net.Conn, m Message) {
	mu.Lock()
	receiverConn, ok := nameToConn[m.To] // находим получателя по имени
	sender := clients[senderConn]        // получаем данные об отправителе
	mu.Unlock()

	if !ok || sender == nil {
		return // если получателя нет — ничего не делаем
	}

	if m.Timestamp == 0 {
		m.Timestamp = time.Now().Unix() // если время не указано — ставим текущее
	}

	m.From = sender.Name // на всякий случай указываем имя отправителя вручную
	data, _ := json.Marshal(m)
	data = append(data, '\n') // добавляем \n, чтобы клиент мог прочитать это как строку

	receiverConn.Write(data) // отправляем получателю

	// Отправляем копию сообщения и отправителю (чтобы у него тоже отобразилось)
	if senderConn != receiverConn {
		senderConn.Write(data)
	}
}

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

// Удаляет клиента из общих структур при отключении
func removeClient(conn net.Conn) {
	mu.Lock()
	if cl, ok := clients[conn]; ok {
		delete(nameToConn, cl.Name) // удаляем по имени
	}
	delete(clients, conn) // удаляем по соединению
	mu.Unlock()

	broadcastUserList() // обновляем список онлайн-пользователей
}
