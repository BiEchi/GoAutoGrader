package server

import (
	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

func Listen(addr string) error {
	router := gin.Default()
	router.LoadHTMLGlob("templates/*")
	router.NoRoute(noRouteHandler)
	router.GET("/ping", pingHandler)
	router.GET("/status", statusHandler)
	router.GET("/gradetest", gradeTestHandler)
	router.POST("/webhook", webhookHandler)
	router.Any("/queue", oauthHandler)
	logrus.Info("Starting server at ", addr)
	return router.Run(addr)
}
