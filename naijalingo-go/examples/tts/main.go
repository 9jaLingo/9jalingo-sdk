package main

import (
	"context"
	"log"
	"os"

	naijalingo "github.com/9jaLingo/9jalingo-sdk/naijalingo-go"
)

func main() {
	client := naijalingo.NewClient(naijalingo.ClientOptions{})
	audio, err := client.TTS.Generate(context.Background(), "Bawo ni, I dey greet you!", naijalingo.GenerateOptions{
		Voice: "adeola_yo",
		Lang:  "yo",
	})
	if err != nil {
		log.Fatal(err)
	}
	if err := os.WriteFile("greeting.wav", audio.Content, 0o644); err != nil {
		log.Fatal(err)
	}
	log.Printf("wrote %d bytes to greeting.wav", len(audio.Content))
}
