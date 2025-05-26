package main

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"os"
)

var DB *pgxpool.Pool

func InitDB() error {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		dsn = "postgres://postgres:n52RO10AD150@localhost:5432/messenger?sslmode=disable"
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var err error
	DB, err = pgxpool.New(ctx, dsn)
	if err != nil {
		return fmt.Errorf("не получилось создать пул: %w", err)
	}

	if err = DB.Ping(ctx); err != nil {
		return fmt.Errorf("БД недоступна: %w", err)
	}

	fmt.Println("✔ PostgreSQL подключена")
	return nil
}
