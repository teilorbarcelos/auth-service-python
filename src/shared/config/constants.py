FEATURES_DATA = {
    "user": {"name": "Usuários", "description": "Gerenciar Usuários"},
    "role": {"name": "Perfis", "description": "Gerenciar Perfis"},
}

ROLES_DATA = {
    "administrator": {
        "name": "Administrador",
        "description": "Administrador do sistema",
        "features": [
            {"key": "user", "create": True, "view": True, "delete": True, "activate": True},
            {"key": "role", "create": True, "view": True, "delete": True, "activate": True},
        ],
    },
    "operator": {
        "name": "Operador",
        "description": "Operador do sistema",
        "features": [
            {"key": "user", "create": False, "view": False, "delete": False, "activate": False},
            {"key": "role", "create": False, "view": False, "delete": False, "activate": False},
        ],
    },
}
