from werkzeug.security import generate_password_hash, check_password_hash

# Simulate registration process
password = "examplePassword"
hashed_during_registration = generate_password_hash(password)
print(f"Hashed during registration: {hashed_during_registration}")

# Simulate login process
same_password = "examplePassword"
verification_result = check_password_hash(hashed_during_registration, same_password)
print(f"Verification result: {verification_result}")