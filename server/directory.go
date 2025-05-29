package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"strings"
)

// handleUserSearch обрабатывает запрос на поиск пользователей по имени или отображаемому имени.
// Получает строку поиска из поля Query, ищет совпадения в базе и возвращает клиенту список подходящих пользователей.
func handleUserSearch(conn net.Conn, m Message) {
	// Удаляем лишние пробелы из запроса
	q := strings.TrimSpace(m.Query)
	if q == "" {
		return // если строка пустая — ничего не ищем
	}

	ctx := context.Background()

	// Выполняем запрос к БД: ищем пользователей, у которых логин или имя содержит подстроку
	rows, err := DB.Query(ctx, `
        SELECT username, display_name
        FROM users
        WHERE username ILIKE $1 OR display_name ILIKE $1
        ORDER BY username
        LIMIT 20
    `, "%"+q+"%")
	if err != nil {
		fmt.Println("Ошибка БД (поиск пользователей):", err)
		return
	}
	defer rows.Close()

	// Сканируем результаты поиска в слайс структур UserSummary
	var results []UserSummary
	for rows.Next() {
		var u UserSummary
		rows.Scan(&u.Username, &u.DisplayName)
		results = append(results, u)
	}

	// Формируем и отправляем клиенту JSON-ответ с найденными пользователями
	resp := Message{Type: "user_search_result", Users: results}
	data, _ := json.Marshal(resp)
	conn.Write(append(data, '\n'))
}
