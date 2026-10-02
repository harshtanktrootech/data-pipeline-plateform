def user_roles(request):
    if not request.user.is_authenticated:
        return {"is_admin": False, "is_operator": False, "is_viewer": False, "user_role": "Guest"}
    
    is_admin = request.user.is_superuser or request.user.groups.filter(name="Admin").exists()
    is_operator = request.user.groups.filter(name="Operator").exists()
    is_viewer = request.user.groups.filter(name="Viewer").exists()

    role = "Admin" if is_admin else ("Operator" if is_operator else ("Viewer" if is_viewer else "User"))
    return {
        "is_admin": is_admin,
        "is_operator": is_operator or is_admin,  # Admins have operator privileges
        "is_viewer": True,
        "user_role": role,
    }
