from apps.accounts.services import get_user_role


def loglens_role(request):
    if request.user.is_authenticated:
        return {"loglens_role": get_user_role(request.user)}
    return {"loglens_role": None}
