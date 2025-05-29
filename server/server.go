package main

import (
	"bufio"
	"encoding/json"
	"net"
)

// Обрабатывает одно клиентское соединение (TCP-сокет).
// Сначала клиент проходит регистрацию или авторизацию,
// затем может отправлять сообщения и выполнять действия.
func handleConnection(conn net.Conn) {
	defer func() {
		removeClient(conn) // При завершении соединения удаляем клиента из памяти
		conn.Close()       // Закрываем сокет
	}()

	scanner := bufio.NewScanner(conn) // Создаём сканер для построчного чтения данных

	// Увеличиваем максимальный размер входящего сообщения до 1 МБ
	buf := make([]byte, 0, 64*1024)
	scanner.Buffer(buf, 1024*1024)

	// Ожидаем первое сообщение — должно быть вход или регистрация
	if !scanner.Scan() {
		return // клиент ничего не прислал
	}

	var initMsg Message
	// Преобразуем JSON-строку в структуру Message
	if err := json.Unmarshal(scanner.Bytes(), &initMsg); err != nil {
		return // если невалидный JSON — отключаемся
	}

	switch initMsg.Type {
	case "signup":
		// Обработка регистрации нового пользователя
		handleSignup(conn, initMsg)
		return // после регистрации соединение закрывается (новый логин потребуется)
	case "signin":
		// Обработка входа: проверка пароля, ответ "login_ok"
		userID, err := handleLogin(conn, initMsg)
		if err != nil {
			// Если авторизация не прошла — просто выходим (ошибка уже отправлена)
			return
		}

		// Сохраняем информацию о клиенте в оперативной памяти
		// Если пользователь уже онлайн — закрываем старое соединение
		removeClientByName(initMsg.From)
		mu.Lock()
		// Сохраняем новое подключение
		clients[conn] = &Client{Conn: conn, Name: initMsg.From, ID: userID}
		nameToConn[initMsg.From] = conn
		mu.Unlock()

	default:
		// Если первое сообщение — не signin/signup — отключаемся
		return
	}

	// Основной цикл приёма всех следующих сообщений от клиента
	for scanner.Scan() {
		var m Message
		// Читаем JSON-строку и преобразуем в структуру
		if err := json.Unmarshal(scanner.Bytes(), &m); err != nil {
			continue // если невалидный JSON — пропускаем
		}

		// Обработка типа сообщения
		switch m.Type {
		case "message":
			handleMessage(conn, m) // отправка личного или группового сообщения
		case "history":
			handleHistoryRequest(conn, m) // запрос истории чата
		case "user_search":
			go handleUserSearch(conn, m) // поиск пользователей (в отдельной горутине)
		case "start_chat":
			go handleStartChat(conn, m) // начать приватный чат
		case "create_group":
			go handleCreateGroup(conn, m) // создать групповой чат
		default:
			// Неизвестный тип сообщения — ничего не делаем
		}
	}
}

// Удаляет клиента из глобальных структур при его отключении
func removeClient(conn net.Conn) {
	mu.Lock()
	if cl, ok := clients[conn]; ok {
		delete(nameToConn, cl.Name) // удаляем по имени пользователя
	}
	delete(clients, conn) // удаляем по соединению
	mu.Unlock()
}

// removeClientByName удаляет клиента по имени пользователя (если он онлайн).
func removeClientByName(username string) {
	mu.Lock()
	if conn, ok := nameToConn[username]; ok {
		conn.Close()                 // Закрываем соединение
		delete(clients, conn)        // Удаляем по соединению
		delete(nameToConn, username) // Удаляем по имени
	}
	mu.Unlock()
}
