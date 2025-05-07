import os
import sys

def setup_env():
    env_file = ".env"
    required_vars = [
        "EMAIL",
        "PASSWORD",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID"
    ]

    if os.path.exists(env_file):
        print(f"'{env_file}' already exists.")
        # Optional: Check if all required vars are present
        try:
            with open(env_file, 'r') as f:
                env_content = f.read()
            missing_vars = [var for var in required_vars if f"{var}=" not in env_content]
            if missing_vars:
                print(f"Warning: The existing '{env_file}' seems to be missing the following variables: {', '.join(missing_vars)}")
                print("You might need to edit it manually or delete it and run this script again.")
            else:
                print("All required variables seem to be present.")
        except Exception as e:
            print(f"Could not read or parse existing '{env_file}': {e}")
        return

    print(f"'{env_file}' not found. Let's create it.")
    env_values = {}
    for var in required_vars:
        while True:
            value = input(f"Enter your {var}: ").strip()
            if value:
                env_values[var] = value
                break
            else:
                print(f"{var} cannot be empty. Please provide a value.")

    try:
        with open(env_file, 'w') as f:
            for var, value in env_values.items():
                # Basic quoting for values with spaces, though proper handling might be needed for complex cases
                if ' ' in value and not (value.startswith('"') and value.endswith('"')):
                    f.write(f'{var}="{value}"\n')
                else:
                    f.write(f"{var}={value}\n")
        print(f"Successfully created '{env_file}'.")
    except IOError as e:
        print(f"Error: Could not write to '{env_file}': {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    print("--- Locket Catcher Setup ---")
    setup_env()
    print("\nSetup complete. You can now run the main script using 'python main.py'.")
