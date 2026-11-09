"""Authorize against the member's current Discord-server roles, never global DB flags."""


def get_user_roles(user_id, member=None):
    denied = {'is_developer': False, 'is_qa': False, 'is_pm': False}
    if member is None or getattr(member, 'id', None) != user_id or not getattr(member, 'guild', None):
        return denied
    roles = getattr(member, 'roles', ())
    names = {role.name for role in roles}
    is_pm = 'Project Manager' in names or getattr(getattr(member, 'guild_permissions', None), 'administrator', False) is True
    return {'is_developer': is_pm or 'Developer' in names,
            'is_qa': is_pm or 'QA' in names, 'is_pm': is_pm}
