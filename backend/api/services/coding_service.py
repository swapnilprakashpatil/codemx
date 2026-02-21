"""
Coding Service – code listing, detail, search, autocomplete, compare, stats, CPT/DHS categories, resources.
"""

from pipeline.models import (
    get_session,
    SnomedCode, ICD10Code, HCCCode, CPTCode, HCPCSCode, RxNormCode, NDCCode,
)


def _paginate(query, page: int = 1, per_page: int = 25) -> dict:
    """Apply pagination to a SQLAlchemy query and return a dict."""
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [item.to_dict() for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


def _build_subcode_tree(subcodes, parent_code: str) -> list[dict]:
    """Build a nested tree of subcodes for a category.

    Given subcodes like A01.0, A01.00, A01.01, A01.1, A01.2, etc.
    produces a tree where A01.0 has children A01.00, A01.01.
    """
    # Index subcodes by their code
    code_map = {s.code: s for s in subcodes}
    all_codes = sorted(code_map.keys())

    # Build parent-child relationships
    # For each code, find its direct parent (the longest prefix that is also in the set)
    children_map: dict[str, list[str]] = {c: [] for c in all_codes}
    top_level: list[str] = []

    for code in all_codes:
        # Walk back through possible parents
        found_parent = False
        # E.g. for "A01.01" → check "A01.0" (remove last char)
        check = code[:-1]
        while len(check) > len(parent_code):
            if check in code_map:
                children_map[check].append(code)
                found_parent = True
                break
            check = check[:-1]
        if not found_parent:
            top_level.append(code)

    def _to_node(code: str) -> dict:
        s = code_map[code]
        return {
            "code": s.code,
            "description": s.description or "",
            "children": [_to_node(c) for c in children_map[code]],
        }

    return [_to_node(c) for c in top_level]


class CodingService:
    """Handles all code-set CRUD, search, autocomplete, compare and stats."""

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _session():
        return get_session()

    # ── autocomplete ─────────────────────────────────────────────────────

    @staticmethod
    def autocomplete(q: str, code_type: str = "", limit: int = 10) -> list[dict]:
        session = CodingService._session()
        suggestions: list[dict] = []
        try:
            term = f"%{q}%"

            if not code_type or code_type == "icd10":
                for r in session.query(ICD10Code).filter(
                    (ICD10Code.code.ilike(term)) | (ICD10Code.description.ilike(term))
                ).limit(limit).all():
                    suggestions.append({"code": r.code, "description": r.description or "", "code_type": "ICD-10-CM"})

            if not code_type or code_type == "hcc":
                for r in session.query(HCCCode).filter(
                    (HCCCode.code.ilike(term)) | (HCCCode.description.ilike(term))
                ).limit(limit).all():
                    suggestions.append({"code": r.code, "description": r.description or "", "code_type": "HCC"})

            if not code_type or code_type == "hcpcs":
                for r in session.query(HCPCSCode).filter(
                    (HCPCSCode.code.ilike(term)) | (HCPCSCode.long_description.ilike(term)) | (HCPCSCode.short_description.ilike(term))
                ).limit(limit).all():
                    suggestions.append({"code": r.code, "description": r.long_description or r.short_description or "", "code_type": "HCPCS"})

            if not code_type or code_type == "snomed":
                for r in session.query(SnomedCode).filter(
                    (SnomedCode.code.ilike(term)) | (SnomedCode.description.ilike(term))
                ).limit(limit).all():
                    suggestions.append({"code": r.code, "description": r.description or "", "code_type": "SNOMED"})

            if not code_type or code_type == "cpt":
                for r in session.query(CPTCode).filter(
                    (CPTCode.code.ilike(term)) | (CPTCode.long_description.ilike(term)) | (CPTCode.short_description.ilike(term))
                ).limit(limit).all():
                    suggestions.append({"code": r.code, "description": r.long_description or r.short_description or "", "code_type": "CPT"})

            if not code_type or code_type == "rxnorm":
                for r in session.query(RxNormCode).filter(
                    (RxNormCode.code.ilike(term)) | (RxNormCode.name.ilike(term))
                ).limit(limit).all():
                    suggestions.append({"code": r.code, "description": r.name or "", "code_type": "RxNorm"})

            if not code_type or code_type == "ndc":
                for r in session.query(NDCCode).filter(
                    (NDCCode.code.ilike(term)) | (NDCCode.product_name.ilike(term))
                ).limit(limit).all():
                    suggestions.append({"code": r.code, "description": r.product_name or "", "code_type": "NDC"})

            return suggestions[:limit]
        finally:
            session.close()

    # ── global search ────────────────────────────────────────────────────

    @staticmethod
    def search(q: str, code_type: str = "", page: int = 1, per_page: int = 25) -> dict:
        session = CodingService._session()
        results: list[dict] = []
        try:
            term = f"%{q}%"

            if not code_type or code_type == "snomed":
                results.extend([s.to_dict() for s in session.query(SnomedCode).filter(
                    (SnomedCode.code.ilike(term)) | (SnomedCode.description.ilike(term))
                ).limit(500).all()])

            if not code_type or code_type == "icd10":
                results.extend([i.to_dict() for i in session.query(ICD10Code).filter(
                    (ICD10Code.code.ilike(term)) | (ICD10Code.description.ilike(term))
                ).limit(500).all()])

            if not code_type or code_type == "hcc":
                results.extend([h.to_dict() for h in session.query(HCCCode).filter(
                    (HCCCode.code.ilike(term)) | (HCCCode.description.ilike(term))
                ).limit(500).all()])

            if not code_type or code_type == "cpt":
                results.extend([c.to_dict() for c in session.query(CPTCode).filter(
                    (CPTCode.code.ilike(term)) | (CPTCode.long_description.ilike(term)) | (CPTCode.short_description.ilike(term))
                ).limit(500).all()])

            if not code_type or code_type == "hcpcs":
                results.extend([h.to_dict() for h in session.query(HCPCSCode).filter(
                    (HCPCSCode.code.ilike(term)) | (HCPCSCode.long_description.ilike(term)) | (HCPCSCode.short_description.ilike(term))
                ).limit(500).all()])

            if not code_type or code_type == "rxnorm":
                results.extend([r.to_dict() for r in session.query(RxNormCode).filter(
                    (RxNormCode.code.ilike(term)) | (RxNormCode.name.ilike(term))
                ).limit(500).all()])

            if not code_type or code_type == "ndc":
                results.extend([r.to_dict() for r in session.query(NDCCode).filter(
                    (NDCCode.code.ilike(term)) | (NDCCode.product_name.ilike(term))
                ).limit(500).all()])

            total = len(results)
            start = (page - 1) * per_page
            return {
                "items": results[start : start + per_page],
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page if total > 0 else 0,
                "query": q,
            }
        finally:
            session.close()

    # ── SNOMED ───────────────────────────────────────────────────────────

    @staticmethod
    def list_snomed(page: int, per_page: int, q: str = "") -> dict:
        session = CodingService._session()
        try:
            query = session.query(SnomedCode).filter_by(active=True)
            if q:
                like = f"%{q}%"
                query = query.filter((SnomedCode.code.ilike(like)) | (SnomedCode.description.ilike(like)))
            return _paginate(query, page, per_page)
        finally:
            session.close()

    @staticmethod
    def get_snomed(code: str) -> dict | None:
        session = CodingService._session()
        try:
            snomed = session.query(SnomedCode).filter_by(code=code).first()
            return snomed.to_dict() if snomed else None
        finally:
            session.close()

    # ── ICD-10 ───────────────────────────────────────────────────────────

    @staticmethod
    def list_icd10(page: int, per_page: int, q: str = "") -> dict:
        session = CodingService._session()
        try:
            query = session.query(ICD10Code).filter_by(active=True)
            if q:
                like = f"%{q}%"
                query = query.filter((ICD10Code.code.ilike(like)) | (ICD10Code.description.ilike(like)))
            return _paginate(query, page, per_page)
        finally:
            session.close()

    @staticmethod
    def list_icd10_hierarchy(letter: str = "", q: str = "") -> dict:
        """Return multi-level hierarchy: Chapters → Categories with child counts.

        When *letter* is provided, returns only chapters containing codes
        starting with that letter, with categories listed inside each chapter.
        When no letter is given, returns all chapters with aggregate counts.
        """
        from sqlalchemy import func
        from .icd10_chapters import ICD10_CHAPTERS, code_in_range, get_chapters_for_letter

        session = CodingService._session()
        try:
            # Determine which chapters to show
            if letter:
                chapters = get_chapters_for_letter(letter.upper())
            else:
                chapters = list(ICD10_CHAPTERS)

            result_chapters = []
            for ch in chapters:
                # Build category query (3-char parent codes within this chapter)
                cat_q = session.query(ICD10Code).filter(
                    ICD10Code.active == True,
                    func.length(ICD10Code.code) == 3,
                    ICD10Code.code >= ch["start"],
                    ICD10Code.code <= ch["end"],
                ).order_by(ICD10Code.code)

                if letter:
                    cat_q = cat_q.filter(ICD10Code.code.like(f"{letter.upper()}%"))

                if q:
                    like = f"%{q}%"
                    # Find parents whose code/description match OR that have matching children
                    child_parent_codes = session.query(
                        func.substr(ICD10Code.code, 1, 3)
                    ).filter(
                        ICD10Code.active == True,
                        func.length(ICD10Code.code) > 3,
                        ICD10Code.code >= ch["start"],
                        ICD10Code.code <= (ch["end"] + "~"),
                        (ICD10Code.code.ilike(like)) | (ICD10Code.description.ilike(like)),
                    ).distinct().subquery()
                    cat_q = cat_q.filter(
                        (ICD10Code.code.ilike(like)) |
                        (ICD10Code.description.ilike(like)) |
                        (ICD10Code.code.in_(session.query(child_parent_codes)))
                    )

                categories = cat_q.all()
                if not categories:
                    continue

                # Get child counts for each category in one query
                child_counts_q = session.query(
                    ICD10Code.category,
                    func.count(ICD10Code.code),
                ).filter(
                    ICD10Code.active == True,
                    func.length(ICD10Code.code) > 3,
                    ICD10Code.category.in_([c.code for c in categories]),
                ).group_by(ICD10Code.category).all()
                child_count_map = dict(child_counts_q)

                cat_list = []
                for c in categories:
                    cat_list.append({
                        "code": c.code,
                        "description": c.description or "",
                        "child_count": child_count_map.get(c.code, 0),
                    })

                result_chapters.append({
                    "id": ch["id"],
                    "name": ch["name"],
                    "range": ch["range"],
                    "category_count": len(cat_list),
                    "categories": cat_list,
                })

            return {"chapters": result_chapters}
        finally:
            session.close()

    @staticmethod
    def get_icd10_category_children(code: str) -> dict:
        """Return a nested tree of subcodes for a 3-char ICD-10 category.

        Builds a multi-level tree: e.g. A01 → A01.0 → A01.00, A01.01
        """
        from sqlalchemy import func

        session = CodingService._session()
        try:
            # Fetch all subcodes for this category
            subcodes = session.query(ICD10Code).filter(
                ICD10Code.active == True,
                ICD10Code.code.like(f"{code}.%"),
            ).order_by(ICD10Code.code).all()

            # Build nested tree based on code structure
            # Group by "base" (chars before the dot + first char after dot)
            tree = _build_subcode_tree(subcodes, code)
            return {"code": code, "children": tree}
        finally:
            session.close()

    @staticmethod
    def get_icd10(code: str) -> dict | None:
        session = CodingService._session()
        try:
            icd10 = session.query(ICD10Code).filter_by(code=code).first()
            return icd10.to_dict() if icd10 else None
        finally:
            session.close()

    # ── HCC ──────────────────────────────────────────────────────────────

    @staticmethod
    def list_hcc(page: int, per_page: int, q: str = "") -> dict:
        session = CodingService._session()
        try:
            query = session.query(HCCCode).filter_by(active=True)
            if q:
                like = f"%{q}%"
                query = query.filter((HCCCode.code.ilike(like)) | (HCCCode.description.ilike(like)))
            return _paginate(query, page, per_page)
        finally:
            session.close()

    @staticmethod
    def get_hcc(code: str) -> dict | None:
        session = CodingService._session()
        try:
            hcc = session.query(HCCCode).filter_by(code=code).first()
            return hcc.to_dict() if hcc else None
        finally:
            session.close()

    # ── CPT ──────────────────────────────────────────────────────────────

    @staticmethod
    def list_cpt(page: int, per_page: int, q: str = "", dhs_only: bool = False) -> dict:
        session = CodingService._session()
        try:
            query = session.query(CPTCode).filter_by(active=True)
            if dhs_only:
                query = query.filter(CPTCode.dhs_category.isnot(None))
            if q:
                like = f"%{q}%"
                query = query.filter(
                    (CPTCode.code.ilike(like)) | (CPTCode.long_description.ilike(like)) | (CPTCode.short_description.ilike(like))
                )
            return _paginate(query, page, per_page)
        finally:
            session.close()

    @staticmethod
    def get_cpt(code: str) -> dict | None:
        session = CodingService._session()
        try:
            cpt = session.query(CPTCode).filter_by(code=code).first()
            return cpt.to_dict() if cpt else None
        finally:
            session.close()

    # ── HCPCS ────────────────────────────────────────────────────────────

    @staticmethod
    def list_hcpcs(page: int, per_page: int, q: str = "", dhs_only: bool = False) -> dict:
        session = CodingService._session()
        try:
            query = session.query(HCPCSCode).filter_by(active=True)
            if dhs_only:
                query = query.filter(HCPCSCode.dhs_category.isnot(None))
            if q:
                like = f"%{q}%"
                query = query.filter(
                    (HCPCSCode.code.ilike(like)) | (HCPCSCode.long_description.ilike(like)) | (HCPCSCode.short_description.ilike(like))
                )
            return _paginate(query, page, per_page)
        finally:
            session.close()

    @staticmethod
    def get_hcpcs(code: str) -> dict | None:
        session = CodingService._session()
        try:
            hcpcs = session.query(HCPCSCode).filter_by(code=code).first()
            return hcpcs.to_dict() if hcpcs else None
        finally:
            session.close()

    # ── RxNorm ───────────────────────────────────────────────────────────

    @staticmethod
    def list_rxnorm(page: int, per_page: int, q: str = "") -> dict:
        session = CodingService._session()
        try:
            query = session.query(RxNormCode).filter_by(active=True)
            if q:
                like = f"%{q}%"
                query = query.filter((RxNormCode.code.ilike(like)) | (RxNormCode.name.ilike(like)))
            return _paginate(query, page, per_page)
        finally:
            session.close()

    @staticmethod
    def get_rxnorm(code: str) -> dict | None:
        session = CodingService._session()
        try:
            rxnorm = session.query(RxNormCode).filter_by(code=code).first()
            return rxnorm.to_dict() if rxnorm else None
        finally:
            session.close()

    # ── NDC ───────────────────────────────────────────────────────────────

    @staticmethod
    def list_ndc(page: int, per_page: int, q: str = "") -> dict:
        session = CodingService._session()
        try:
            query = session.query(NDCCode).filter_by(active=True)
            if q:
                like = f"%{q}%"
                query = query.filter((NDCCode.code.ilike(like)) | (NDCCode.product_name.ilike(like)))
            return _paginate(query, page, per_page)
        finally:
            session.close()

    @staticmethod
    def get_ndc(code: str) -> dict | None:
        session = CodingService._session()
        try:
            ndc = session.query(NDCCode).filter_by(code=code).first()
            return ndc.to_dict() if ndc else None
        finally:
            session.close()

    # ── CPT / DHS Categories ──────────────────────────────────────────────────

    @staticmethod
    def list_dhs(page: int, per_page: int, category: str = "") -> dict:
        session = CodingService._session()
        try:
            cpt_q = session.query(CPTCode).filter(CPTCode.dhs_category.isnot(None))
            if category:
                cpt_q = cpt_q.filter(CPTCode.dhs_category.ilike(f"%{category}%"))
            cpt_codes = cpt_q.all()

            hcpcs_q = session.query(HCPCSCode).filter(HCPCSCode.dhs_category.isnot(None))
            if category:
                hcpcs_q = hcpcs_q.filter(HCPCSCode.dhs_category.ilike(f"%{category}%"))
            hcpcs_codes = hcpcs_q.all()

            all_codes = [c.to_dict() for c in cpt_codes] + [c.to_dict() for c in hcpcs_codes]
            all_codes.sort(key=lambda x: x["code"])

            total = len(all_codes)
            start = (page - 1) * per_page
            return {
                "items": all_codes[start : start + per_page],
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page,
            }
        finally:
            session.close()

    @staticmethod
    def list_dhs_categories() -> dict:
        from sqlalchemy import func

        session = CodingService._session()
        try:
            cpt_cats = (
                session.query(CPTCode.dhs_category, func.count(CPTCode.code))
                .filter(CPTCode.dhs_category.isnot(None))
                .group_by(CPTCode.dhs_category)
                .all()
            )
            hcpcs_cats = (
                session.query(HCPCSCode.dhs_category, func.count(HCPCSCode.code))
                .filter(HCPCSCode.dhs_category.isnot(None))
                .group_by(HCPCSCode.dhs_category)
                .all()
            )
            cat_counts: dict = {}
            for cat, cnt in cpt_cats:
                cat_counts[cat] = cat_counts.get(cat, {"cpt": 0, "hcpcs": 0})
                cat_counts[cat]["cpt"] = cnt
            for cat, cnt in hcpcs_cats:
                cat_counts[cat] = cat_counts.get(cat, {"cpt": 0, "hcpcs": 0})
                cat_counts[cat]["hcpcs"] = cnt

            categories = [
                {"category": cat, "cpt_count": d["cpt"], "hcpcs_count": d["hcpcs"], "total": d["cpt"] + d["hcpcs"]}
                for cat, d in sorted(cat_counts.items())
            ]
            return {"categories": categories, "total_categories": len(categories)}
        finally:
            session.close()

    # ── Compare ──────────────────────────────────────────────────────────

    @staticmethod
    def compare(codes: list[str]) -> list[dict]:
        session = CodingService._session()
        results: list[dict] = []
        try:
            for code in codes:
                found = False
                for Model in (SnomedCode, ICD10Code, HCCCode, CPTCode, HCPCSCode, RxNormCode, NDCCode):
                    obj = session.query(Model).filter_by(code=code).first()
                    if obj:
                        results.append(obj.to_dict())
                        found = True
                if not found:
                    results.append({"code": code, "error": "Code not found in any coding set"})
            return results
        finally:
            session.close()

    # ── Stats ────────────────────────────────────────────────────────────

    @staticmethod
    def get_stats() -> dict:
        from pipeline.models import (
            snomed_icd10_mapping, icd10_hcc_mapping,
            snomed_hcc_mapping, rxnorm_snomed_mapping, ndc_rxnorm_mapping,
        )

        session = CodingService._session()
        try:
            return {
                "snomed_codes": session.query(SnomedCode).count(),
                "icd10_codes": session.query(ICD10Code).count(),
                "hcc_codes": session.query(HCCCode).count(),
                "cpt_codes": session.query(CPTCode).count(),
                "hcpcs_codes": session.query(HCPCSCode).count(),
                "rxnorm_codes": session.query(RxNormCode).count(),
                "ndc_codes": session.query(NDCCode).count(),
                "snomed_icd10_mappings": len(session.execute(snomed_icd10_mapping.select()).fetchall()),
                "icd10_hcc_mappings": len(session.execute(icd10_hcc_mapping.select()).fetchall()),
                "snomed_hcc_mappings": len(session.execute(snomed_hcc_mapping.select()).fetchall()),
                "rxnorm_snomed_mappings": len(session.execute(rxnorm_snomed_mapping.select()).fetchall()),
                "ndc_rxnorm_mappings": len(session.execute(ndc_rxnorm_mapping.select()).fetchall()),
            }
        finally:
            session.close()

    # ── Resources (static data) ──────────────────────────────────────────

    @staticmethod
    def get_resources() -> dict:
        return {
            "guidelines": [
                {
                    "title": "ICD-10-CM Official Guidelines for Coding and Reporting",
                    "url": "https://www.cms.gov/medicare/coding-billing/icd-10-codes/icd-10-cm-official-guidelines-coding-and-reporting",
                    "category": "ICD-10-CM",
                    "description": "Official coding guidelines from CMS for ICD-10-CM coding.",
                },
                {
                    "title": "CMS HCC Risk Adjustment Model",
                    "url": "https://www.cms.gov/medicare/health-plans/medicareadvtgspecratestats/risk-adjustors",
                    "category": "HCC",
                    "description": "CMS risk adjustment model documentation and updates.",
                },
                {
                    "title": "SNOMED CT Browser",
                    "url": "https://browser.ihtsdotools.org/",
                    "category": "SNOMED",
                    "description": "Official SNOMED CT browser for searching and browsing concepts.",
                },
                {
                    "title": "AMA CPT Code Lookup",
                    "url": "https://www.ama-assn.org/practice-management/cpt",
                    "category": "CPT",
                    "description": "American Medical Association CPT code resources.",
                },
                {
                    "title": "CMS HCPCS Coding Questions",
                    "url": "https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system",
                    "category": "HCPCS",
                    "description": "CMS resources for HCPCS Level II coding.",
                },
            ],
            "training": [
                {
                    "title": "CMS MLN (Medicare Learning Network)",
                    "url": "https://www.cms.gov/outreach-and-education/medicare-learning-network-mln/mlngeninfo",
                    "description": "Free educational materials for healthcare professionals.",
                },
                {
                    "title": "AHIMA Coding Education",
                    "url": "https://www.ahima.org/",
                    "description": "American Health Information Management Association training.",
                },
                {
                    "title": "AAPC Coding Resources",
                    "url": "https://www.aapc.com/",
                    "description": "American Academy of Professional Coders resources.",
                },
            ],
            "updates": [
                {
                    "title": "ICD-10-CM Updates (FY2026)",
                    "description": "Annual ICD-10-CM code updates effective October 1, 2025.",
                    "effective_date": "2025-10-01",
                },
                {
                    "title": "HCC Model V28 Phase-In",
                    "description": "CMS HCC risk adjustment model V28 phase-in continues.",
                    "effective_date": "2026-01-01",
                },
            ],
        }
