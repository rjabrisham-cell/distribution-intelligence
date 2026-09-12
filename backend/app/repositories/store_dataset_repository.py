"""One explicit store dataset boundary. Never infer legacy membership."""

from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import String, cast

from app.core.enums import EntityType, ImportStatus
from app.models.file import File
from app.models.import_batch import ImportBatch
from app.models.import_store_row import ImportStoreRow
from app.models.project import Project


class StoreDatasetRepository:
    def __init__(self, db):
        self.db = db

    def active_batch(self, project_id):
        return self.db.query(ImportBatch).join(
            Project, Project.active_store_batch_id == ImportBatch.id,
        ).join(File, File.id == ImportBatch.file_id).filter(
            Project.id == project_id, File.entity_type == "PROJECT",
            File.entity_id == project_id, File.category == "stores",
            File.removed_at.is_(None), ImportBatch.entity_type == EntityType.STORE,
            ImportBatch.status.in_([ImportStatus.COMPLETED, ImportStatus.COMPLETED_WITH_ERRORS]),
        ).first()

    def rows(self, batch_id):
        return self.db.query(ImportStoreRow).filter(
            ImportStoreRow.batch_id == batch_id,
        ).order_by(ImportStoreRow.row_number).all()

    def row(self, batch_id, row_number):
        return self.db.query(ImportStoreRow).filter_by(
            batch_id=batch_id, row_number=row_number,
        ).one_or_none()

    def record(self, batch_id, company_store_id, row_number, snapshot):
        self.db.add(ImportStoreRow(batch_id=batch_id, company_store_id=company_store_id,
                                   row_number=row_number, snapshot=snapshot))
        self.db.flush()

    def activate(self, project_id, batch):
        # Same lock order as removal; publish only a complete set of accepted rows.
        project = self.db.query(Project).filter_by(id=project_id).populate_existing().with_for_update().one()
        file = self.db.query(File).filter_by(id=batch.file_id).populate_existing().with_for_update().one()
        if (file.entity_type != "PROJECT" or file.entity_id != project_id
                or file.category != "stores" or file.removed_at is not None):
            raise ValueError("Store import source is not an available project file")
        if batch.entity_type != EntityType.STORE or batch.status not in (ImportStatus.COMPLETED, ImportStatus.COMPLETED_WITH_ERRORS):
            raise ValueError("Store batch is not complete")
        count = self.db.query(ImportStoreRow).filter_by(batch_id=batch.id).count()
        if not count or count != batch.imported_rows:
            raise ValueError("Store batch membership is incomplete")
        newer = self.db.query(ImportBatch.id).join(File, File.id == ImportBatch.file_id).filter(
            File.entity_type == "PROJECT", File.entity_id == project_id,
            File.category == "stores", ImportBatch.entity_type == EntityType.STORE,
            ImportBatch.id > batch.id,
            ImportBatch.status.in_([ImportStatus.COMPLETED, ImportStatus.COMPLETED_WITH_ERRORS]),
        ).first()
        if newer:
            return  # An older in-flight import must not replace a later dataset.
        project.active_store_batch_id = batch.id

    def remove_file(self, file):
        project = self.db.query(Project).filter_by(id=file.entity_id).populate_existing().with_for_update().one()
        file = self.db.query(File).filter_by(id=file.id).populate_existing().with_for_update().one()
        active = self.db.get(ImportBatch, project.active_store_batch_id) if project.active_store_batch_id else None
        if active is not None and active.file_id == file.id:
            project.active_store_batch_id = None
        if file.removed_at is None:
            file.removed_at = datetime.now(timezone.utc)
        self.db.commit()

    @staticmethod
    def input_view(company, snapshot):
        """Input for this batch, never a previous batch's mutable company fields."""
        return SimpleNamespace(
            id=company.id, master_store_id=company.master_store_id,
            name=snapshot.get("name") or snapshot.get("canonical_name"),
            phone=snapshot.get("phone") or snapshot.get("canonical_phone"),
            address=snapshot.get("address"), postal_code=snapshot.get("postal_code"),
            province=snapshot.get("province_name"), city=snapshot.get("city_name"),
            latitude=snapshot.get("latitude"), longitude=snapshot.get("longitude"),
        )

    def audit_rows(self, project_id, batch_id):
        from app.models.company_store import CompanyStore
        from app.models.store import Store
        from app.models.address_candidate import AddressCandidate
        source = "import_batch:" + cast(ImportStoreRow.batch_id, String) + ":row:" + cast(ImportStoreRow.row_number, String)
        return self.db.query(ImportStoreRow, CompanyStore, Store, AddressCandidate).join(
            CompanyStore, CompanyStore.id == ImportStoreRow.company_store_id,
        ).outerjoin(Store, Store.id == CompanyStore.master_store_id).outerjoin(
            AddressCandidate,
            (AddressCandidate.company_store_id == CompanyStore.id)
            & (AddressCandidate.source_type == "excel") & (AddressCandidate.source_id == source),
        ).join(ImportBatch, ImportBatch.id == ImportStoreRow.batch_id).join(
            Project, Project.active_store_batch_id == ImportBatch.id,
        ).join(File, File.id == ImportBatch.file_id).filter(
            Project.id == project_id, ImportStoreRow.batch_id == batch_id,
            File.entity_type == "PROJECT", File.entity_id == project_id,
            File.category == "stores", File.removed_at.is_(None),
            ImportBatch.entity_type == EntityType.STORE,
            ImportBatch.status.in_([ImportStatus.COMPLETED, ImportStatus.COMPLETED_WITH_ERRORS]),
        ).order_by(
            ImportStoreRow.row_number, AddressCandidate.id.desc(),
        ).all()

    def candidate_query(self, batch_id):
        from app.models.address_candidate import AddressCandidate
        source = "import_batch:" + cast(ImportStoreRow.batch_id, String) + ":row:" + cast(ImportStoreRow.row_number, String)
        return self.db.query(AddressCandidate).join(
            ImportStoreRow, (ImportStoreRow.company_store_id == AddressCandidate.company_store_id)
            & (AddressCandidate.source_id == source),
        ).join(ImportBatch, ImportBatch.id == ImportStoreRow.batch_id).join(
            Project, Project.active_store_batch_id == ImportBatch.id,
        ).join(File, File.id == ImportBatch.file_id).filter(
            ImportStoreRow.batch_id == batch_id, AddressCandidate.source_type == "excel",
            File.removed_at.is_(None), File.entity_type == "PROJECT",
            File.entity_id == Project.id, File.category == "stores",
        )

    def require_active_for_write(self, project_id, batch_id):
        project = self.db.query(Project).filter_by(id=project_id).populate_existing().with_for_update().one()
        active = self.active_batch(project_id)
        if project.active_store_batch_id != batch_id or active is None or active.id != batch_id:
            raise ValueError("Matching requires the active store dataset")
