from enum import Enum

class binTypes(Enum):
    BIO = "bio"
    REST = "rest"
    PAPIER = "papier"
    GELB = "gelb"

    @classmethod
    def from_string(cls, value: str):
        """Wandelt einen String in das passende Enum-Mitglied um."""
        for item in cls:
            if item.value == value:
                return item
        raise ValueError(f"{value} ist keine gültige Müllart!")

def open_bin(type: binTypes):
    print(f"Der {type.value.upper()}-Müll wurde geöffnet.")
