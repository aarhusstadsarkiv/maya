class LEGAL:
    NO_OTHER_RESTRICTIONS: int = 1
    """1. Materialet er ikke underlagt andre juridiske begrænsninger."""

    PERSONAL_DATA: int = 2
    """2. Materialet er utilgængeligt ifølge persondatalovgivningen."""

    ARCHIVE_LAW: int = 3
    """3. Materialet er utilgængeligt ifølge arkivlovgivningen."""

    SPECIAL_CIRCUMSTANCES: int = 4
    """4. Materialet er utilgængeligt som følge af særlige juridiske forhold."""


class CONTRACT:
    UNAVAILABLE: int = 1
    """1. Materialet er utilgængeligt. Ifølge aftale."""

    APPLICATION_ONLY: int = 2
    """2. Materialet er kun tilgængeligt gennem ansøgning. Ifølge aftale."""

    READING_ROOM: int = 3
    """3. Materialet må kun ses på læsesalen. Ifølge aftale."""

    INTERNET: int = 4
    """4. Materialet må offentliggøres på internettet/kun på Aarhus Stadsarkivs hjemmesider. Ifølge aftale."""


class AVAILABILITY:
    IN_STORAGE: int = 2
    """2. Materialet skal bestilles hjem til læsesalen, før det kan beses."""

    IN_READING_ROOM: int = 3
    """3. Materialet er tilgængeligt på læsesalen."""

    ONLINE_ACCESS: int = 4
    """4. Materialet er tilgængeligt online."""


class USABILITY:
    PUBLIC_DOMAIN: int = 1
    """1. I offentlig eje."""

    CC_BY: int = 2
    """2. CC Navngivelse."""

    CC_BY_NC: int = 3
    """3. CC Navngivelse-IkkeKommerciel."""

    ALL_RIGHTS_RESERVED: int = 4
    """4. Alle rettigheder forbeholdes."""
