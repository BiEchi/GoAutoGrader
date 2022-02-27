package main

import (
	"autograder/klc3"
	"autograder/repo"
	"autograder/server"
	"io"
	"os"
	"time"

	"github.com/sirupsen/logrus"
)

func init() {
	// init logrus
	logrus.SetReportCaller(true)
	logrus.SetFormatter(&logrus.JSONFormatter{})
	file, err := os.OpenFile("./logs/server.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0666)
	if err != nil {
		logrus.Fatal(err)
	}
	mw := io.MultiWriter(os.Stdout, file)
	logrus.SetOutput(mw)
}

func main() {
	klc3Repo, err := repo.GetKlc3Repo()
	if err != nil { logrus.Fatal(err) }
	if err := klc3Repo.AutoSync(); err != nil { logrus.Fatal(err) }
	if err := klc3.StartQueue(4, 400, time.Minute*10); err != nil { logrus.Fatal(err) }
	if err := server.Listen("0.0.0.0:8080"); err != nil { logrus.Fatal(err) }
}
