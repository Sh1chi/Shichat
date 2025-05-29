package main

import (
	"context"
	"encoding/json"
	"fmt"
	"golang.org/x/crypto/bcrypt"
	"net"
)

// handleSignup обрабатывает регистрацию нового пользователя.
// Проверяет корректность данных, наличие такого логина, хэширует пароль
// и сохраняет нового пользователя в базу данных.
func handleSignup(conn net.Conn, m Message) {
	// Проверка обязательных полей: логин, пароль и имя не должны быть пустыми
	if m.From == "" || m.Password == "" || m.FirstName == "" {
		sendError(conn, "Логин, имя и пароль обязательны")
		return
	}
	username := m.From
	pwd := m.Password
	first := m.FirstName
	last := m.LastName // фамилия может быть не указана

	// Проверяем, существует ли уже пользователь с таким логином
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

	// Хэшируем пароль с помощью bcrypt
	hashBytes, err := bcrypt.GenerateFromPassword([]byte(pwd), bcrypt.DefaultCost)
	if err != nil {
		sendError(conn, "Ошибка хеширования пароля")
		return
	}
	hashed := string(hashBytes)

	// Сохраняем нового пользователя в таблицу users
	_, err = DB.Exec(context.Background(), `
        INSERT INTO users (username, first_name, last_name, password_hash)
        VALUES ($1, $2, $3, $4)
    `, username, first, last, hashed)
	if err != nil {
		sendError(conn, "Ошибка сохранения")
		return
	}

	// Отправляем клиенту сообщение об успешной регистрации
	resp := Message{Type: "signup_ok", Content: "Регистрация прошла успешно"}
	data, _ := json.Marshal(resp)
	conn.Write(append(data, '\n'))
}

// handleLogin обрабатывает вход пользователя по логину и паролю.
// Если данные верны — возвращает ID пользователя и отправляет клиенту подтверждение.
func handleLogin(conn net.Conn, m Message) (userID int64, err error) {
	username := m.From
	pwd := m.Password

	// Ищем пользователя по логину и получаем его ID и хэш пароля
	var hashInDB string
	err = DB.QueryRow(context.Background(),
		`SELECT id, password_hash FROM users WHERE username = $1`, username,
	).Scan(&userID, &hashInDB)
	if err != nil {
		sendError(conn, "Пользователь не найден")
		return 0, err
	}

	// Проверяем, что переданный пароль совпадает с хэшем
	if err := bcrypt.CompareHashAndPassword([]byte(hashInDB), []byte(pwd)); err != nil {
		sendError(conn, "Неверный пароль")
		return 0, fmt.Errorf("auth failed")
	}

	// Обновляем дату и время последнего входа
	if _, err := DB.Exec(context.Background(),
		`UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = $1`,
		userID,
	); err != nil {
		// Ошибка не критична — просто выводим в лог
		fmt.Println("DB warning: не удалось обновить last_login_at:", err)
	}

	// Отправляем сообщение об успешном входе
	resp := Message{Type: "login_ok", Content: "OK"}
	data, _ := json.Marshal(resp)
	conn.Write(append(data, '\n'))

	// Отправляем клиенту список доступных чатов
	sendChatList(conn, userID)
	return userID, nil
}

// sendError отправляет клиенту сообщение об ошибке с переданным текстом.
func sendError(conn net.Conn, text string) {
	resp := Message{
		Type:    "error",
		Content: text,
	}
	data, _ := json.Marshal(resp)
	conn.Write(append(data, '\n'))
}
