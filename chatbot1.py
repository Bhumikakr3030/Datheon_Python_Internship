print("Welcome to My Alex Assistant!")
print("Type 'bye' to exit.")

while True:
    user_input = input("You: ").lower()

    if user_input == "hello":
        print("Alex: Hi!")

    elif user_input == "how are you":
        print("Alex: I'm fine, thanks!")

    elif user_input == "bye":
        print("Alex: Goodbye!")
        break

    else:
        print("Alex: Sorry, I don't understand.")
