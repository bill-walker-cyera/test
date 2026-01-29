import os
from typing import Any, Dict, Iterable, List

from simple_salesforce import Salesforce


class SfdcClient:
    def __init__(self, salesforce: Salesforce) -> None:
        self.salesforce = salesforce

    @classmethod
    def from_env(cls) -> "SfdcClient":
        version = os.environ.get("SFDC_API_VERSION")
        access_token = os.environ.get("SFDC_ACCESS_TOKEN")
        instance_url = os.environ.get("SFDC_INSTANCE_URL")
        if access_token and instance_url:
            salesforce = Salesforce(session_id=access_token, instance_url=instance_url, version=version)
            return cls(salesforce)

        username = os.environ.get("SFDC_USERNAME")
        password = os.environ.get("SFDC_PASSWORD")
        security_token = os.environ.get("SFDC_SECURITY_TOKEN")
        domain = os.environ.get("SFDC_DOMAIN", "login")

        if not username or not password or not security_token:
            raise ValueError(
                "Missing Salesforce auth. Set SFDC_ACCESS_TOKEN/SFDC_INSTANCE_URL "
                "or SFDC_USERNAME/SFDC_PASSWORD/SFDC_SECURITY_TOKEN."
            )

        salesforce = Salesforce(
            username=username,
            password=password,
            security_token=security_token,
            domain=domain,
            version=version,
        )
        return cls(salesforce)

    def bulk_upsert(
        self,
        object_name: str,
        records: Iterable[Dict[str, Any]],
        external_id_field: str,
        batch_size: int = 2000,
        use_serial: bool = True,
    ) -> List[Dict[str, Any]]:
        if not object_name:
            raise ValueError("Salesforce object name is required.")
        if not external_id_field:
            raise ValueError("Salesforce external ID field is required for upserts.")

        records_list = list(records)
        if not records_list:
            return []

        bulk_object = getattr(self.salesforce.bulk, object_name)
        return bulk_object.upsert(records_list, external_id_field, batch_size=batch_size, use_serial=use_serial)
