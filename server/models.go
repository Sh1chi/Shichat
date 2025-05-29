package main

import (
	"net"
	"sync"
)

// Структура описывает формат всех сообщений между клиентом и сервером
// Каждое поле может использоваться в зависимости от типа сообщения
type Message struct {
	Type         string        `json:"type"`                   // Тип сообщения: "signup", "signin", "message", "history", "userlist" и т.д.
	From         string        `json:"from,omitempty"`         // Имя отправителя (username)
	To           string        `json:"to,omitempty"`           // Имя получателя или ID чата (для групп)
	Content      string        `json:"content,omitempty"`      // Текст сообщения
	Password     string        `json:"password,omitempty"`     // Пароль (для входа или регистрации)
	FirstName    string        `json:"first_name,omitempty"`   // Имя пользователя
	LastName     string        `json:"last_name,omitempty"`    // Фамилия пользователя
	Query        string        `json:"query,omitempty"`        // Поисковый запрос (например, поиск пользователей)
	Name         string        `json:"name,omitempty"`         // Название новой группы
	Participants []string      `json:"participants,omitempty"` // Участники группы
	Timestamp    int64         `json:"timestamp,omitempty"`    // Время отправки сообщения (Unix-время)
	DisplayName  string        `json:"display_name,omitempty"` // Имя, отображаемое в интерфейсе
	Chats        []ChatPreview `json:"chats,omitempty"`        // Список чатов (используется при передаче chatlist)
	Users        []UserSummary `json:"users,omitempty"`        // Список пользователей (результат поиска)
	Chat         *ChatPreview  `json:"chat,omitempty"`         // Данные одного чата
}

// Структура, описывающая краткую информацию о чате (для отображения в списке чатов)
type ChatPreview struct {
	ChatID      int64  `json:"chat_id"`      // Уникальный ID чата
	Peer        string `json:"peer"`         // Имя собеседника (для приватного чата)
	DisplayName string `json:"display_name"` // Название группы или имя собеседника
	LastMsg     string `json:"last_msg"`     // Последнее сообщение
	LastTS      int64  `json:"last_ts"`      // Время последнего сообщения (Unix-время)
}

// Структура для краткой информации о пользователе (используется в поиске пользователей)
type UserSummary struct {
	Username    string `json:"username"`     // Логин пользователя
	DisplayName string `json:"display_name"` // Отображаемое имя (имя + фамилия)
}

// Структура клиента, подключённого к серверу
type Client struct {
	Conn net.Conn // TCP-соединение клиента
	Name string   // Имя пользователя (username)
	ID   int64    // ID пользователя из базы данных
}

// Глобальные переменные для отслеживания активных соединений
var (
	clients    = make(map[net.Conn]*Client) // Сопоставляет соединение с данными клиента
	nameToConn = make(map[string]net.Conn)  // Позволяет найти соединение по имени пользователя
	mu         sync.Mutex                   // Защищает от одновременного доступа из разных горутин
)
