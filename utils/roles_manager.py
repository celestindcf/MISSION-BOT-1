import discord
from discord.ext import commands
import config
import json
import os

class RolesManager:
    def __init__(self, bot):
        self.bot = bot
        self.config = config.load_config()
    
    def reload_config(self):
        self.config = config.load_config()
    
    def get_role_name(self, role_key):
        return self.config["roles"].get(role_key, {}).get("name", role_key.capitalize())
    
    def get_role_id(self, role_key):
        return self.config["roles"].get(role_key, {}).get("id")
    
    async def update_role_name(self, role_key, new_name):
        self.config["roles"][role_key]["name"] = new_name
        config.save_config(self.config)
    
    async def update_role_id(self, role_key, role_id):
        self.config["roles"][role_key]["id"] = role_id
        config.save_config(self.config)
    
    async def add_override(self, user_id, roles=[], permissions=[]):
        user_id_str = str(user_id)
        if user_id_str not in self.config["overrides"]:
            self.config["overrides"][user_id_str] = {"roles": [], "permissions": []}
        if roles:
            self.config["overrides"][user_id_str]["roles"] = roles
        if permissions:
            self.config["overrides"][user_id_str]["permissions"] = permissions
        config.save_config(self.config)
    
    async def remove_override(self, user_id):
        user_id_str = str(user_id)
        if user_id_str in self.config["overrides"]:
            del self.config["overrides"][user_id_str]
            config.save_config(self.config)
    
    def get_permissions_for_user(self, user_id, guild):
        permissions = set()
        user_id_str = str(user_id)
        
        # Permissions des rôles
        for role_key, role_data in self.config["roles"].items():
            role_id = role_data.get("id")
            if role_id:
                role = discord.utils.get(guild.roles, id=role_id)
                if role:
                    member = guild.get_member(user_id)
                    if member and role in member.roles:
                        permissions.update(role_data.get("permissions", []))
        
        # Override permissions
        if user_id_str in self.config.get("overrides", {}):
            override = self.config["overrides"][user_id_str]
            permissions.update(override.get("permissions", []))
            # Si le rôle "commandant" est dans l'override
            if "commandant" in override.get("roles", []):
                permissions.update(self.config["roles"]["commandant"].get("permissions", []))
        
        return list(permissions)
    
    async def add_permission_to_user(self, user_id, permission):
        user_id_str = str(user_id)
        if user_id_str not in self.config["overrides"]:
            self.config["overrides"][user_id_str] = {"roles": [], "permissions": []}
        if permission not in self.config["overrides"][user_id_str]["permissions"]:
            self.config["overrides"][user_id_str]["permissions"].append(permission)
            config.save_config(self.config)
            return True
        return False
    
    async def remove_permission_from_user(self, user_id, permission):
        user_id_str = str(user_id)
        if user_id_str in self.config.get("overrides", {}):
            if permission in self.config["overrides"][user_id_str]["permissions"]:
                self.config["overrides"][user_id_str]["permissions"].remove(permission)
                config.save_config(self.config)
                return True
        return False
    
    async def add_role_to_user_override(self, user_id, role_key):
        user_id_str = str(user_id)
        if user_id_str not in self.config["overrides"]:
            self.config["overrides"][user_id_str] = {"roles": [], "permissions": []}
        if role_key not in self.config["overrides"][user_id_str]["roles"]:
            self.config["overrides"][user_id_str]["roles"].append(role_key)
            config.save_config(self.config)
            return True
        return False
    
    async def remove_role_from_user_override(self, user_id, role_key):
        user_id_str = str(user_id)
        if user_id_str in self.config.get("overrides", {}):
            if role_key in self.config["overrides"][user_id_str]["roles"]:
                self.config["overrides"][user_id_str]["roles"].remove(role_key)
                config.save_config(self.config)
                return True
        return False
    
    def is_commandant(self, user_id, guild):
        user_id_str = str(user_id)
        
        # Vérifier override
        if user_id_str in self.config.get("overrides", {}):
            if "commandant" in self.config["overrides"][user_id_str].get("roles", []):
                return True
        
        # Vérifier rôle
        role_id = self.config["roles"].get("commandant", {}).get("id")
        if role_id:
            role = discord.utils.get(guild.roles, id=role_id)
            if role:
                member = guild.get_member(user_id)
                if member and role in member.roles:
                    return True
        return False

def is_commandant(user_id, guild):
    """Fonction utilitaire pour vérifier si un utilisateur est commandant"""
    roles_manager = RolesManager(None)
    return roles_manager.is_commandant(user_id, guild)
