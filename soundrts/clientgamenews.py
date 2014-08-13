def must_be_said(nb):
    if nb <= 10:
        return True
    elif nb <= 100:
        return nb % 10 == 0
    else:
        return nb % 100 == 0
