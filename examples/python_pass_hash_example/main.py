from werkzeug.security import check_password_hash, generate_password_hash

pw_unhashed = "password"
pw_hashed = generate_password_hash(pw_unhashed, method='sha256')
print(type(pw_hashed))


result = check_password_hash(pw_hashed, pw_unhashed)

print(result)
