"""
Enterprise Data Model v4.0
Model Registry

Import order is important.

All SQLAlchemy model classes must be imported here
so that SQLAlchemy can resolve string-based relationship
references during mapper configuration.

## Architecture

Base
├── Account
├── Company
│    ├── Project
│    └── CompanyStore
│
├── ProjectCompanyStore
│    └── Project ↔ CompanyStore
│
├── Store
│    ├── StoreLocation
│    └── AddressCandidate
│
├── File
├── Request
├── RequestFile
├── ImportBatch
├── RowError
│
├── Driver
│    ├── VehicleDriver
│    └── ProjectDriver
│
├── Vehicle
│    ├── VehicleDriver
│    └── ProjectVehicle
│
├── Order
└── GPSRecord

## Important Architecture Rules

1. Company owns Vehicle.

2. Company owns Driver.

3. Project belongs to Company.

4. VehicleDriver represents the operational assignment
   between Vehicle and Driver.

5. ProjectVehicle represents project-specific usage
   of a Vehicle.

6. ProjectDriver represents project-specific usage
   of a Driver.

7. ProjectVehicle does NOT own Vehicle.

8. ProjectDriver does NOT own Driver.

9. Deleting a Project deletes its association records:

   ```
   ProjectVehicle
   ProjectDriver
   ProjectCompanyStore
   ```

10. Deleting a Project MUST NOT delete:

    Vehicle
    Driver
    CompanyStore

11. A CompanyStore may be used by multiple Projects.

12. A Vehicle may participate in multiple Projects
    over its lifecycle.

13. A Driver may participate in multiple Projects
    over its lifecycle.

14. ImportBatch represents the source/import event only.
    It does not define ownership of Vehicle or Driver.

## SQLAlchemy Mapper Registration

The import order below ensures that all model classes
participating in string-based relationships are imported
before configure_mappers() is executed.
"""

# ==========================================================

# Base

# ==========================================================

from app.models.base import (
Base,
BaseModel,
)

# ==========================================================

# Security / Account

# ==========================================================

from app.models.account import (
Account,
)

# ==========================================================

# Enterprise Identity

# ==========================================================

from app.models.company import (
Company,
)

from app.models.project import (
Project,
ProjectStatus,
)

# ==========================================================

# Enterprise Truth Layer

# ==========================================================

from app.models.store import (
Store,
)

from app.models.store_location import (
StoreLocation,
)

from app.models.address_candidate import (
AddressCandidate,
)

# ==========================================================

# Company-Owned Store Layer

# ==========================================================

from app.models.company_store import (
CompanyStore,
)

# ==========================================================

# Project ↔ CompanyStore Association

# ==========================================================

from app.models.project_company_store import (
ProjectCompanyStore,
)

# ==========================================================

# File Management

# ==========================================================

from app.models.file import (
File,
)

# ==========================================================

# Request System

# ==========================================================

from app.models.request import (
Request,
)

from app.models.request_file import (
RequestFile,
)

# ==========================================================

# Import Engine

# ==========================================================

from app.models.import_batch import (
ImportBatch,
)

from app.models.row_error import (
RowError,
)

# ==========================================================

# Operational Resources

# ==========================================================

# ----------------------------------------------------------

# Driver

# ----------------------------------------------------------

from app.models.driver import (
Driver,
)

# ----------------------------------------------------------

# Vehicle

# ----------------------------------------------------------

from app.models.vehicle import (
Vehicle,
)

# ----------------------------------------------------------

# Vehicle ↔ Driver Assignment

# ----------------------------------------------------------

from app.models.vehicle_driver import (
VehicleDriver,
)

# ----------------------------------------------------------

# Project ↔ Vehicle Association

# ----------------------------------------------------------

from app.models.project_vehicle import (
ProjectVehicle,
)

# ----------------------------------------------------------

# Project ↔ Driver Association

# ----------------------------------------------------------

from app.models.project_driver import (
ProjectDriver,
)

# ----------------------------------------------------------

# Orders

# ----------------------------------------------------------

from app.models.order import (
Order,
)

# ----------------------------------------------------------

# GPS Records

# ----------------------------------------------------------

from app.models.gps_record import (
GPSRecord,
)

# ==========================================================

# Public API

# ==========================================================

__all__ = [

# ------------------------------------------------------
# Base
# ------------------------------------------------------

"Base",
"BaseModel",


# ------------------------------------------------------
# Security
# ------------------------------------------------------

"Account",


# ------------------------------------------------------
# Enterprise Identity
# ------------------------------------------------------

"Company",
"Project",
"ProjectStatus",


# ------------------------------------------------------
# Enterprise Truth Layer
# ------------------------------------------------------

"Store",
"StoreLocation",
"AddressCandidate",


# ------------------------------------------------------
# Company-Owned Store Layer
# ------------------------------------------------------

"CompanyStore",


# ------------------------------------------------------
# Project ↔ CompanyStore
# ------------------------------------------------------

"ProjectCompanyStore",


# ------------------------------------------------------
# File Management
# ------------------------------------------------------

"File",


# ------------------------------------------------------
# Request System
# ------------------------------------------------------

"Request",
"RequestFile",


# ------------------------------------------------------
# Import Engine
# ------------------------------------------------------

"ImportBatch",
"RowError",


# ------------------------------------------------------
# Operational Resources
# ------------------------------------------------------

"Driver",
"Vehicle",
"VehicleDriver",
"ProjectVehicle",
"ProjectDriver",
"Order",
"GPSRecord",

]
