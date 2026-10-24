print("Welcome to My Alex Ai Assistant!")
print("Type 'bye' to exit.")

while True:
    user_input = input("You: ").lower()

    if user_input == "hello":
        print("Alex: Hi!")

    elif user_input == "how are you":
        print("Alex: I'm fine, thanks!")

    elif user_input == "What are your hours of operation?":
        print("Alex: We operate Monday through Friday from 9:00 AM to 6:00 PM IST.")

    elif user_input == "How do I submit my internship project?":
        print("Alex: You can submit your public GitHub repository link through your Student Workspace")

    elif user_input == "When will I receive my certificate?":
        print("Alex: Certificates are reviewed and issued within 3-5 business days after your code review.")


    elif user_input == "bye":
        print("Alex: Goodbye!")
        break

    else:
        print("Alex: Sorry, I don't understand.")
