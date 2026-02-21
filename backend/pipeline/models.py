"""
Database models for the Coding Manager application.
Defines SQLAlchemy ORM models for all medical coding sets and their mappings.
"""

import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean,
    DateTime, ForeignKey, Table, Index
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "coding_manager.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

Base = declarative_base()

# ─── Association Tables (Many-to-Many) ────────────────────────────────────────

snomed_icd10_mapping = Table(
    "snomed_icd10_mapping",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("snomed_code", String(20), ForeignKey("snomed_codes.code"), nullable=False),
    Column("icd10_code", String(10), ForeignKey("icd10_codes.code"), nullable=False),
    Column("map_group", Integer),
    Column("map_priority", Integer),
    Column("map_rule", String(255)),
    Column("map_advice", String(500)),
    Column("correlation_id", String(20)),
    Column("map_category_id", String(20)),
    Column("active", Boolean, default=True),
    Column("effective_date", String(10)),
)

snomed_hcc_mapping = Table(
    "snomed_hcc_mapping",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("snomed_code", String(20), ForeignKey("snomed_codes.code"), nullable=False),
    Column("hcc_code", String(10), ForeignKey("hcc_codes.code"), nullable=False),
    Column("via_icd10_code", String(10), nullable=True),
    Column("active", Boolean, default=True),
)

icd10_hcc_mapping = Table(
    "icd10_hcc_mapping",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("icd10_code", String(10), ForeignKey("icd10_codes.code"), nullable=False),
    Column("hcc_code", String(10), ForeignKey("hcc_codes.code"), nullable=False),
    Column("payment_year", Integer),
    Column("model_version", String(10)),
    Column("active", Boolean, default=True),
)

snomed_cpt_mapping = Table(
    "snomed_cpt_mapping",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("snomed_code", String(20), ForeignKey("snomed_codes.code"), nullable=False),
    Column("cpt_code", String(10), ForeignKey("cpt_codes.code"), nullable=False),
    Column("active", Boolean, default=True),
)

snomed_hcpcs_mapping = Table(
    "snomed_hcpcs_mapping",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("snomed_code", String(20), ForeignKey("snomed_codes.code"), nullable=False),
    Column("hcpcs_code", String(10), ForeignKey("hcpcs_codes.code"), nullable=False),
    Column("active", Boolean, default=True),
)

rxnorm_snomed_mapping = Table(
    "rxnorm_snomed_mapping",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("rxnorm_code", String(20), ForeignKey("rxnorm_codes.code"), nullable=False),
    Column("snomed_code", String(20), ForeignKey("snomed_codes.code"), nullable=False),
    Column("relationship", String(50)),
    Column("active", Boolean, default=True),
)

rxnorm_relationships = Table(
    "rxnorm_relationships",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("rxcui_source", String(20), ForeignKey("rxnorm_codes.code"), nullable=False),
    Column("rxcui_target", String(20), ForeignKey("rxnorm_codes.code"), nullable=False),
    Column("relationship", String(50), nullable=False),  # has_ingredient, tradename_of, etc.
)

ndc_rxnorm_mapping = Table(
    "ndc_rxnorm_mapping",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ndc_code", String(20), ForeignKey("ndc_codes.code"), nullable=False),
    Column("rxnorm_code", String(20), ForeignKey("rxnorm_codes.code"), nullable=False),
    Column("source", String(50)),  # "rxnorm_ndc_codes" or "direct_match"
    Column("active", Boolean, default=True),
)


# ─── ORM Models ──────────────────────────────────────────────────────────────

class SnomedCode(Base):
    """SNOMED CT (Systematized Nomenclature of Medicine - Clinical Terms)"""
    __tablename__ = "snomed_codes"

    code = Column(String(20), primary_key=True)
    description = Column(Text, nullable=False)
    fully_specified_name = Column(Text)
    semantic_tag = Column(String(100))
    active = Column(Boolean, default=True)
    module_id = Column(String(20))
    effective_date = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    icd10_codes = relationship(
        "ICD10Code", secondary=snomed_icd10_mapping, back_populates="snomed_codes"
    )
    hcc_codes = relationship(
        "HCCCode", secondary=snomed_hcc_mapping, back_populates="snomed_codes"
    )
    cpt_codes = relationship(
        "CPTCode", secondary=snomed_cpt_mapping, back_populates="snomed_codes"
    )
    hcpcs_codes = relationship(
        "HCPCSCode", secondary=snomed_hcpcs_mapping, back_populates="snomed_codes"
    )
    rxnorm_codes = relationship(
        "RxNormCode", secondary=rxnorm_snomed_mapping, back_populates="snomed_codes"
    )

    def to_dict(self):
        return {
            "code": self.code,
            "description": self.description,
            "fully_specified_name": self.fully_specified_name,
            "semantic_tag": self.semantic_tag,
            "module_id": self.module_id,
            "effective_date": self.effective_date,
            "active": self.active,
            "code_type": "SNOMED",
        }


class ICD10Code(Base):
    """ICD-10-CM (International Classification of Diseases, 10th Revision, Clinical Modification)"""
    __tablename__ = "icd10_codes"

    code = Column(String(10), primary_key=True)
    description = Column(Text, nullable=False)
    short_description = Column(String(255))
    category = Column(String(10))
    chapter = Column(String(100))
    is_header = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    effective_date = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    snomed_codes = relationship(
        "SnomedCode", secondary=snomed_icd10_mapping, back_populates="icd10_codes"
    )
    hcc_codes = relationship(
        "HCCCode", secondary=icd10_hcc_mapping, back_populates="icd10_codes"
    )

    def to_dict(self):
        return {
            "code": self.code,
            "description": self.description,
            "short_description": self.short_description,
            "category": self.category,
            "chapter": self.chapter,
            "is_header": self.is_header,
            "effective_date": self.effective_date,
            "active": self.active,
            "code_type": "ICD-10-CM",
        }


class HCCCode(Base):
    """HCC (Hierarchical Condition Category) for risk adjustment"""
    __tablename__ = "hcc_codes"

    code = Column(String(10), primary_key=True)
    description = Column(Text, nullable=False)
    category = Column(String(100))
    coefficient = Column(String(20))
    model_version = Column(String(10))
    payment_year = Column(Integer)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    snomed_codes = relationship(
        "SnomedCode", secondary=snomed_hcc_mapping, back_populates="hcc_codes"
    )
    icd10_codes = relationship(
        "ICD10Code", secondary=icd10_hcc_mapping, back_populates="hcc_codes"
    )

    def to_dict(self):
        return {
            "code": self.code,
            "description": self.description,
            "category": self.category,
            "coefficient": self.coefficient,
            "model_version": self.model_version,
            "payment_year": self.payment_year,
            "active": self.active,
            "code_type": "HCC",
        }


class CPTCode(Base):
    """CPT (Current Procedural Terminology) codes"""
    __tablename__ = "cpt_codes"

    code = Column(String(10), primary_key=True)
    short_description = Column(String(255))
    long_description = Column(Text, nullable=False)
    category = Column(String(100))
    dhs_category = Column(String(100), nullable=True)  # DHS Designated Health Service category
    status = Column(String(20), default="Active")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    snomed_codes = relationship(
        "SnomedCode", secondary=snomed_cpt_mapping, back_populates="cpt_codes"
    )

    def to_dict(self):
        return {
            "code": self.code,
            "short_description": self.short_description,
            "long_description": self.long_description,
            "category": self.category,
            "dhs_category": self.dhs_category,
            "status": self.status,
            "active": self.active,
            "code_type": "CPT",
        }


class HCPCSCode(Base):
    """HCPCS (Healthcare Common Procedure Coding System) Level II codes"""
    __tablename__ = "hcpcs_codes"

    code = Column(String(10), primary_key=True)
    short_description = Column(String(255))
    long_description = Column(Text, nullable=False)
    category = Column(String(100))
    dhs_category = Column(String(100), nullable=True)  # DHS Designated Health Service category
    status = Column(String(20), default="Active")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    snomed_codes = relationship(
        "SnomedCode", secondary=snomed_hcpcs_mapping, back_populates="hcpcs_codes"
    )

    def to_dict(self):
        return {
            "code": self.code,
            "short_description": self.short_description,
            "long_description": self.long_description,
            "category": self.category,
            "dhs_category": self.dhs_category,
            "status": self.status,
            "active": self.active,
            "code_type": "HCPCS",
        }


class RxNormCode(Base):
    """RxNorm drug codes (ingredients, clinical drugs, branded drugs)"""
    __tablename__ = "rxnorm_codes"

    # TTY label mapping for display
    TTY_LABELS = {
        "IN": "Ingredient",
        "BN": "Brand Name",
        "SCD": "Semantic Clinical Drug",
        "SBD": "Semantic Branded Drug",
        "PIN": "Precise Ingredient",
        "MIN": "Multiple Ingredients",
        "SCDF": "Semantic Clinical Drug Form",
        "SBDF": "Semantic Branded Drug Form",
        "DF": "Dose Form",
    }

    code = Column(String(20), primary_key=True)  # RXCUI
    name = Column(Text, nullable=False)
    term_type = Column(String(10))  # IN, BN, SCD, SBD, etc.
    suppress = Column(String(5))
    active = Column(Boolean, default=True)
    rxterm_form = Column(String(100))           # RXTERM_FORM: "Oral Tablet", "Injectable"
    available_strength = Column(Text)           # RXN_AVAILABLE_STRENGTH: "10 MG", "25 MG"
    strength = Column(String(100))              # RXN_STRENGTH: "10 MG/ML"
    human_drug = Column(Boolean)                # RXN_HUMAN_DRUG
    vet_drug = Column(Boolean)                  # RXN_VET_DRUG
    bn_cardinality = Column(String(10))         # RXN_BN_CARDINALITY: single/multi
    ndc_codes = Column(Text)                    # NDC codes (pipe-separated)
    quantity = Column(String(50))               # RXN_QUANTITY: e.g. "30"
    qualitative_distinction = Column(Text)      # RXN_QUALITATIVE_DISTINCTION
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    snomed_codes = relationship(
        "SnomedCode", secondary=rxnorm_snomed_mapping, back_populates="rxnorm_codes"
    )
    ndc_codes_rel = relationship(
        "NDCCode", secondary="ndc_rxnorm_mapping", back_populates="rxnorm_codes"
    )

    def to_dict(self):
        return {
            "code": self.code,
            "name": self.name,
            "description": self.name,
            "term_type": self.term_type,
            "term_type_label": self.TTY_LABELS.get(self.term_type, self.term_type),
            "rxterm_form": self.rxterm_form,
            "available_strength": self.available_strength,
            "strength": self.strength,
            "human_drug": self.human_drug,
            "vet_drug": self.vet_drug,
            "bn_cardinality": self.bn_cardinality,
            "ndc_codes": self.ndc_codes.split("|") if self.ndc_codes else [],
            "quantity": self.quantity,
            "qualitative_distinction": self.qualitative_distinction,
            "suppress": self.suppress,
            "active": self.active,
            "code_type": "RxNorm",
        }


class NDCCode(Base):
    """NDC (National Drug Code) - FDA drug product codes"""
    __tablename__ = "ndc_codes"

    code = Column(String(20), primary_key=True)  # NDC in 11-digit format (no dashes)
    product_ndc = Column(String(20))  # Product NDC (5-4 or 4-4 format)
    package_ndc = Column(String(20))  # Package NDC (11-digit)
    product_name = Column(Text, nullable=False)
    proprietary_name = Column(String(500))  # Brand name
    non_proprietary_name = Column(String(500))  # Generic name
    dosage_form = Column(String(200))
    route = Column(String(200))
    strength = Column(String(200))
    active_ingredient = Column(Text)
    product_type = Column(String(50))  # HUMAN PRESCRIPTION DRUG, OTC, etc.
    marketing_category = Column(String(100))  # NDA, ANDA, etc.
    application_number = Column(String(50))
    labeler_name = Column(String(500))
    listing_record_certified_through = Column(String(20))  # Date
    dea_schedule = Column(String(10))  # C-II, C-III, etc.
    ndc_exclude_flag = Column(String(10))  # Y/N
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rxnorm_codes = relationship(
        "RxNormCode", secondary="ndc_rxnorm_mapping", back_populates="ndc_codes_rel"
    )

    def to_dict(self):
        return {
            "code": self.code,
            "product_ndc": self.product_ndc,
            "package_ndc": self.package_ndc,
            "description": self.product_name,
            "product_name": self.product_name,
            "proprietary_name": self.proprietary_name,
            "non_proprietary_name": self.non_proprietary_name,
            "dosage_form": self.dosage_form,
            "route": self.route,
            "strength": self.strength,
            "active_ingredient": self.active_ingredient,
            "product_type": self.product_type,
            "marketing_category": self.marketing_category,
            "application_number": self.application_number,
            "labeler_name": self.labeler_name,
            "listing_record_certified_through": self.listing_record_certified_through,
            "dea_schedule": self.dea_schedule,
            "ndc_exclude_flag": self.ndc_exclude_flag,
            "active": self.active,
            "code_type": "NDC",
        }


class MappingConflict(Base):
    """Records that could not be mapped during pipeline processing."""
    __tablename__ = "mapping_conflicts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_system = Column(String(20), nullable=False)     # e.g. 'SNOMED', 'ICD-10', 'HCC'
    target_system = Column(String(20), nullable=False)     # e.g. 'ICD-10', 'HCC'
    source_code = Column(String(30), nullable=False)       # The code that failed to map
    target_code = Column(String(30), nullable=True)        # The target code that was missing
    source_description = Column(Text, nullable=True)       # Description of source code if available
    reason = Column(String(100), nullable=False)           # e.g. 'source_not_found', 'target_not_found'
    details = Column(Text, nullable=True)                  # Extra context (map_rule, map_advice, etc.)
    status = Column(String(20), default="open")            # open, resolved, ignored
    resolution = Column(Text, nullable=True)               # How it was resolved
    resolved_code = Column(String(30), nullable=True)      # The final mapped code
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "source_system": self.source_system,
            "target_system": self.target_system,
            "source_code": self.source_code,
            "target_code": self.target_code,
            "source_description": self.source_description,
            "reason": self.reason,
            "details": self.details,
            "status": self.status,
            "resolution": self.resolution,
            "resolved_code": self.resolved_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


# ─── Indexes ──────────────────────────────────────────────────────────────────

Index("idx_snomed_description", SnomedCode.description)
Index("idx_icd10_description", ICD10Code.description)
Index("idx_icd10_category", ICD10Code.category)
Index("idx_hcc_description", HCCCode.description)
Index("idx_cpt_description", CPTCode.long_description)
Index("idx_hcpcs_description", HCPCSCode.long_description)
Index("idx_rxnorm_name", RxNormCode.name)
Index("idx_rxnorm_term_type", RxNormCode.term_type)
Index("idx_ndc_product_name", NDCCode.product_name)
Index("idx_ndc_product_ndc", NDCCode.product_ndc)
Index("idx_conflict_status", MappingConflict.status)
Index("idx_conflict_source", MappingConflict.source_system, MappingConflict.source_code)
Index("idx_conflict_target", MappingConflict.target_system)


# ─── Database Initialization ─────────────────────────────────────────────────

def get_engine():
    """Create and return a SQLAlchemy engine."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    engine = create_engine(DATABASE_URL, echo=False)
    return engine


def init_db():
    """Initialize the database - create all tables and apply migrations."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    # Apply column migrations for existing databases
    _apply_migrations(engine)
    print(f"Database initialized at: {DB_PATH}")
    return engine


def _apply_migrations(engine):
    """Add columns that may be missing from older database schemas."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    migrations = [
        ("cpt_codes", "dhs_category", "VARCHAR(100)"),
        ("hcpcs_codes", "dhs_category", "VARCHAR(100)"),
        # RxNorm enrichment columns
        ("rxnorm_codes", "rxterm_form", "VARCHAR(100)"),
        ("rxnorm_codes", "available_strength", "TEXT"),
        ("rxnorm_codes", "strength", "VARCHAR(100)"),
        ("rxnorm_codes", "human_drug", "BOOLEAN"),
        ("rxnorm_codes", "vet_drug", "BOOLEAN"),
        ("rxnorm_codes", "bn_cardinality", "VARCHAR(10)"),
        ("rxnorm_codes", "ndc_codes", "TEXT"),
        ("rxnorm_codes", "quantity", "VARCHAR(50)"),
        ("rxnorm_codes", "qualitative_distinction", "TEXT"),
    ]
    for table, column, col_type in migrations:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    # Create rxnorm_relationships table if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rxnorm_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rxcui_source VARCHAR(20) NOT NULL REFERENCES rxnorm_codes(code),
            rxcui_target VARCHAR(20) NOT NULL REFERENCES rxnorm_codes(code),
            relationship VARCHAR(50) NOT NULL
        )
    """)
    # Add index for efficient lookups
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rxrel_source ON rxnorm_relationships(rxcui_source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rxrel_target ON rxnorm_relationships(rxcui_target)")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def get_session():
    """Create and return a new database session."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


if __name__ == "__main__":
    init_db()
    print("All tables created successfully.")
