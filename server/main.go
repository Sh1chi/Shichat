package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"net"
	"sync"
)

type Message struct {
	From    string `json:"from"`
	Content string `json:"content"`
}

var (
	clients = make(map[net.Conn]string)
	lock    sync.Mutex
)

func main() {
	ln, err := net.Listen("tcp", ":8080")
	if err != nil {
		panic(err)
	}
	defer ln.Close()
	fmt.Println("Сервер запущен на порту 8080...")

	for {
		conn, err := ln.Accept()
		if err != nil {
			continue
		}
		go handleClient(conn)
	}
}

func handleClient(conn net.Conn) {
	defer func() {
		lock.Lock()
		delete(clients, conn)
		lock.Unlock()
		conn.Close()
	}()

	reader := bufio.NewScanner(conn)

	lock.Lock()
	clients[conn] = conn.RemoteAddr().String()
	lock.Unlock()

	for reader.Scan() {
		var msg Message
		err := json.Unmarshal(reader.Bytes(), &msg)
		if err != nil {
			continue
		}
		broadcast(msg, conn)
	}
}

func broadcast(msg Message, sender net.Conn) {
	data, _ := json.Marshal(msg)
	data = append(data, '\n')
	lock.Lock()
	conns := make([]net.Conn, 0, len(clients))
	for c := range clients {
		conns = append(conns, c)
	}
	lock.Unlock()

	for _, c := range conns {
		if _, err := c.Write(data); err != nil {
			lock.Lock()
			delete(clients, c)
			lock.Unlock()
			c.Close()
		}
	}
}
