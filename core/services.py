def format_zahl(wert, stellen=2, trailing_zeros=True):
    text = f"{wert:.{stellen}f}".replace(".", ",")
    return text.rstrip(",0") if not trailing_zeros and "," in text else text

