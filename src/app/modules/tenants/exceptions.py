class TenantSlugTakenError(Exception):
    def __init__(self, slug: str) -> None:
        super().__init__(f"Tenant slug '{slug}' is already taken")
        self.slug = slug