"""
Mapping Service – directional mapping lookups, code-detail enrichment, mapping graph.
"""

from pipeline.models import (
    get_session,
    SnomedCode, ICD10Code, HCCCode, CPTCode, HCPCSCode, RxNormCode, NDCCode,
    snomed_icd10_mapping, snomed_hcc_mapping, icd10_hcc_mapping,
    snomed_cpt_mapping, snomed_hcpcs_mapping, rxnorm_snomed_mapping,
    rxnorm_relationships, ndc_rxnorm_mapping,
)


class MappingService:
    """Cross-system mapping lookups and the mapping-graph builder."""

    @staticmethod
    def _session():
        return get_session()

    # ── SNOMED detail with all mappings ──────────────────────────────────

    @staticmethod
    def get_snomed_detail(code: str) -> dict | None:
        session = MappingService._session()
        try:
            snomed = session.query(SnomedCode).filter_by(code=code).first()
            if not snomed:
                return None

            result = snomed.to_dict()

            # ICD-10 mappings
            rows = session.execute(
                snomed_icd10_mapping.select().where(snomed_icd10_mapping.c.snomed_code == code)
            ).fetchall()
            result["icd10_mappings"] = []
            for m in rows:
                icd10 = session.query(ICD10Code).filter_by(code=m.icd10_code).first()
                if icd10:
                    d = icd10.to_dict()
                    d["map_rule"] = m.map_rule
                    d["map_advice"] = m.map_advice
                    result["icd10_mappings"].append(d)

            # HCC mappings
            rows = session.execute(
                snomed_hcc_mapping.select().where(snomed_hcc_mapping.c.snomed_code == code)
            ).fetchall()
            result["hcc_mappings"] = []
            for m in rows:
                hcc = session.query(HCCCode).filter_by(code=m.hcc_code).first()
                if hcc:
                    d = hcc.to_dict()
                    d["via_icd10_code"] = m.via_icd10_code
                    result["hcc_mappings"].append(d)

            # CPT mappings
            rows = session.execute(
                snomed_cpt_mapping.select().where(snomed_cpt_mapping.c.snomed_code == code)
            ).fetchall()
            result["cpt_mappings"] = []
            for m in rows:
                cpt = session.query(CPTCode).filter_by(code=m.cpt_code).first()
                if cpt:
                    result["cpt_mappings"].append(cpt.to_dict())

            # HCPCS mappings
            rows = session.execute(
                snomed_hcpcs_mapping.select().where(snomed_hcpcs_mapping.c.snomed_code == code)
            ).fetchall()
            result["hcpcs_mappings"] = []
            for m in rows:
                hcpcs = session.query(HCPCSCode).filter_by(code=m.hcpcs_code).first()
                if hcpcs:
                    result["hcpcs_mappings"].append(hcpcs.to_dict())

            # RxNorm mappings
            rows = session.execute(
                rxnorm_snomed_mapping.select().where(rxnorm_snomed_mapping.c.snomed_code == code)
            ).fetchall()
            result["rxnorm_mappings"] = []
            for m in rows:
                rxnorm = session.query(RxNormCode).filter_by(code=m.rxnorm_code).first()
                if rxnorm:
                    result["rxnorm_mappings"].append(rxnorm.to_dict())

            return result
        finally:
            session.close()

    # ── ICD-10 detail with mappings ──────────────────────────────────────

    @staticmethod
    def get_icd10_detail(code: str) -> dict | None:
        session = MappingService._session()
        try:
            icd10 = session.query(ICD10Code).filter_by(code=code).first()
            if not icd10:
                return None

            result = icd10.to_dict()

            # SNOMED mappings
            rows = session.execute(
                snomed_icd10_mapping.select().where(snomed_icd10_mapping.c.icd10_code == code)
            ).fetchall()
            result["snomed_mappings"] = []
            for m in rows:
                snomed = session.query(SnomedCode).filter_by(code=m.snomed_code).first()
                if snomed:
                    result["snomed_mappings"].append(snomed.to_dict())

            # HCC mappings
            rows = session.execute(
                icd10_hcc_mapping.select().where(icd10_hcc_mapping.c.icd10_code == code)
            ).fetchall()
            result["hcc_mappings"] = []
            for m in rows:
                hcc = session.query(HCCCode).filter_by(code=m.hcc_code).first()
                if hcc:
                    result["hcc_mappings"].append(hcc.to_dict())

            return result
        finally:
            session.close()

    # ── HCC detail with mappings ─────────────────────────────────────────

    @staticmethod
    def get_hcc_detail(code: str) -> dict | None:
        session = MappingService._session()
        try:
            hcc = session.query(HCCCode).filter_by(code=code).first()
            if not hcc:
                return None

            result = hcc.to_dict()

            # ICD-10 mappings
            rows = session.execute(
                icd10_hcc_mapping.select().where(icd10_hcc_mapping.c.hcc_code == code)
            ).fetchall()
            result["icd10_mappings"] = []
            for m in rows:
                icd10 = session.query(ICD10Code).filter_by(code=m.icd10_code).first()
                if icd10:
                    result["icd10_mappings"].append(icd10.to_dict())

            # SNOMED mappings
            rows = session.execute(
                snomed_hcc_mapping.select().where(snomed_hcc_mapping.c.hcc_code == code)
            ).fetchall()
            result["snomed_mappings"] = []
            for m in rows:
                snomed = session.query(SnomedCode).filter_by(code=m.snomed_code).first()
                if snomed:
                    result["snomed_mappings"].append(snomed.to_dict())

            return result
        finally:
            session.close()

    # ── RxNorm detail with mappings ──────────────────────────────────────

    @staticmethod
    def get_cpt_detail(code: str) -> dict | None:
        session = MappingService._session()
        try:
            cpt = session.query(CPTCode).filter_by(code=code).first()
            if not cpt:
                return None

            result = cpt.to_dict()

            # SNOMED mappings
            rows = session.execute(
                snomed_cpt_mapping.select().where(snomed_cpt_mapping.c.cpt_code == code)
            ).fetchall()
            result["snomed_mappings"] = []
            for m in rows:
                snomed = session.query(SnomedCode).filter_by(code=m.snomed_code).first()
                if snomed:
                    result["snomed_mappings"].append(snomed.to_dict())

            return result
        finally:
            session.close()

    @staticmethod
    def get_hcpcs_detail(code: str) -> dict | None:
        session = MappingService._session()
        try:
            hcpcs = session.query(HCPCSCode).filter_by(code=code).first()
            if not hcpcs:
                return None

            result = hcpcs.to_dict()

            # SNOMED mappings
            rows = session.execute(
                snomed_hcpcs_mapping.select().where(snomed_hcpcs_mapping.c.hcpcs_code == code)
            ).fetchall()
            result["snomed_mappings"] = []
            for m in rows:
                snomed = session.query(SnomedCode).filter_by(code=m.snomed_code).first()
                if snomed:
                    result["snomed_mappings"].append(snomed.to_dict())

            return result
        finally:
            session.close()

    @staticmethod
    def get_rxnorm_detail(code: str) -> dict | None:
        """Return RxNorm code details with SNOMED mappings and inter-concept relationships."""
        session = MappingService._session()
        try:
            rxnorm = session.query(RxNormCode).filter_by(code=code).first()
            if not rxnorm:
                return None

            result = rxnorm.to_dict()

            # SNOMED mappings
            rows = session.execute(
                rxnorm_snomed_mapping.select().where(rxnorm_snomed_mapping.c.rxnorm_code == code)
            ).fetchall()
            result["snomed_mappings"] = []
            for m in rows:
                snomed = session.query(SnomedCode).filter_by(code=m.snomed_code).first()
                if snomed:
                    result["snomed_mappings"].append(snomed.to_dict())

            # NDC mappings
            rows = session.execute(
                ndc_rxnorm_mapping.select().where(ndc_rxnorm_mapping.c.rxnorm_code == code)
            ).fetchall()
            result["ndc_mappings"] = []
            for m in rows:
                ndc = session.query(NDCCode).filter_by(code=m.ndc_code).first()
                if ndc:
                    result["ndc_mappings"].append(ndc.to_dict())

            # RxNorm inter-concept relationships (ingredients, brand names, dose forms)
            rel_rows = session.execute(
                rxnorm_relationships.select().where(rxnorm_relationships.c.rxcui_source == code)
            ).fetchall()

            ingredients = []
            brand_names = []
            dose_forms = []
            related = []
            for r in rel_rows:
                target = session.query(RxNormCode).filter_by(code=r.rxcui_target).first()
                if not target:
                    continue
                entry = target.to_dict()
                if r.relationship == "has_ingredient":
                    ingredients.append(entry)
                elif r.relationship == "tradename_of":
                    brand_names.append(entry)
                elif r.relationship == "has_dose_form":
                    dose_forms.append(entry)
                else:
                    entry["relationship"] = r.relationship
                    related.append(entry)

            # Also check reverse relationships (e.g., if this is an ingredient, find drugs containing it)
            rev_rows = session.execute(
                rxnorm_relationships.select().where(rxnorm_relationships.c.rxcui_target == code)
            ).fetchall()

            contained_in = []
            brand_of = []
            for r in rev_rows:
                source = session.query(RxNormCode).filter_by(code=r.rxcui_source).first()
                if not source:
                    continue
                entry = source.to_dict()
                if r.relationship == "has_ingredient":
                    contained_in.append(entry)
                elif r.relationship == "tradename_of":
                    brand_of.append(entry)
                elif r.relationship == "has_dose_form":
                    dose_forms.append(entry)

            if ingredients:
                result["ingredients"] = ingredients
            if brand_names:
                result["brand_names"] = brand_names
            if dose_forms:
                result["dose_forms"] = dose_forms
            if related:
                result["related_concepts"] = related
            if contained_in:
                result["contained_in"] = contained_in[:50]  # cap for display
            if brand_of:
                result["brand_of"] = brand_of[:50]

            return result
        finally:
            session.close()

    # ── NDC detail ────────────────────────────────────────────────────────

    @staticmethod
    def get_ndc_detail(code: str) -> dict | None:
        session = MappingService._session()
        try:
            ndc = session.query(NDCCode).filter_by(code=code).first()
            if not ndc:
                return None
            
            result = ndc.to_dict()
            
            # RxNorm mappings
            rows = session.execute(
                ndc_rxnorm_mapping.select().where(ndc_rxnorm_mapping.c.ndc_code == code)
            ).fetchall()
            result["rxnorm_mappings"] = []
            for m in rows:
                rxnorm = session.query(RxNormCode).filter_by(code=m.rxnorm_code).first()
                if rxnorm:
                    result["rxnorm_mappings"].append(rxnorm.to_dict())
            
            return result
        finally:
            session.close()

    # ── Directional mapping endpoints ────────────────────────────────────

    @staticmethod
    def snomed_to_icd10(snomed_code: str) -> dict:
        session = MappingService._session()
        try:
            mappings = session.execute(
                snomed_icd10_mapping.select().where(snomed_icd10_mapping.c.snomed_code == snomed_code)
            ).fetchall()
            results = []
            for m in mappings:
                icd10 = session.query(ICD10Code).filter_by(code=m.icd10_code).first()
                if icd10:
                    d = icd10.to_dict()
                    d["map_group"] = m.map_group
                    d["map_priority"] = m.map_priority
                    d["map_rule"] = m.map_rule
                    d["map_advice"] = m.map_advice
                    results.append(d)
            return {"snomed_code": snomed_code, "icd10_mappings": results, "total": len(results)}
        finally:
            session.close()

    @staticmethod
    def snomed_to_hcc(snomed_code: str) -> dict:
        session = MappingService._session()
        try:
            mappings = session.execute(
                snomed_hcc_mapping.select().where(snomed_hcc_mapping.c.snomed_code == snomed_code)
            ).fetchall()
            results = []
            for m in mappings:
                hcc = session.query(HCCCode).filter_by(code=m.hcc_code).first()
                if hcc:
                    d = hcc.to_dict()
                    d["via_icd10_code"] = m.via_icd10_code
                    results.append(d)
            return {"snomed_code": snomed_code, "hcc_mappings": results, "total": len(results)}
        finally:
            session.close()

    @staticmethod
    def icd10_to_hcc(icd10_code: str) -> dict:
        session = MappingService._session()
        try:
            mappings = session.execute(
                icd10_hcc_mapping.select().where(icd10_hcc_mapping.c.icd10_code == icd10_code)
            ).fetchall()
            results = []
            for m in mappings:
                hcc = session.query(HCCCode).filter_by(code=m.hcc_code).first()
                if hcc:
                    results.append(hcc.to_dict())
            return {"icd10_code": icd10_code, "hcc_mappings": results, "total": len(results)}
        finally:
            session.close()

    @staticmethod
    def rxnorm_to_snomed(rxnorm_code: str) -> dict:
        session = MappingService._session()
        try:
            mappings = session.execute(
                rxnorm_snomed_mapping.select().where(rxnorm_snomed_mapping.c.rxnorm_code == rxnorm_code)
            ).fetchall()
            results = []
            for m in mappings:
                snomed = session.query(SnomedCode).filter_by(code=m.snomed_code).first()
                if snomed:
                    results.append(snomed.to_dict())
            return {"rxnorm_code": rxnorm_code, "snomed_mappings": results, "total": len(results)}
        finally:
            session.close()

    @staticmethod
    def ndc_to_rxnorm(ndc_code: str) -> dict:
        session = MappingService._session()
        try:
            mappings = session.execute(
                ndc_rxnorm_mapping.select().where(ndc_rxnorm_mapping.c.ndc_code == ndc_code)
            ).fetchall()
            results = []
            for m in mappings:
                rxnorm = session.query(RxNormCode).filter_by(code=m.rxnorm_code).first()
                if rxnorm:
                    results.append(rxnorm.to_dict())
            return {"ndc_code": ndc_code, "rxnorm_mappings": results, "total": len(results)}
        finally:
            session.close()

    @staticmethod
    def rxnorm_to_ndc(rxnorm_code: str) -> dict:
        session = MappingService._session()
        try:
            mappings = session.execute(
                ndc_rxnorm_mapping.select().where(ndc_rxnorm_mapping.c.rxnorm_code == rxnorm_code)
            ).fetchall()
            results = []
            for m in mappings:
                ndc = session.query(NDCCode).filter_by(code=m.ndc_code).first()
                if ndc:
                    results.append(ndc.to_dict())
            return {"rxnorm_code": rxnorm_code, "ndc_mappings": results, "total": len(results)}
        finally:
            session.close()

    # ── Mapping graph ────────────────────────────────────────────────────

    @staticmethod
    def get_mapping_graph(code: str) -> dict | None:
        session = MappingService._session()
        nodes: dict = {}
        edges: list[dict] = []

        def add_node(code_val, label, code_type, category=""):
            key = f"{code_type}:{code_val}"
            if key not in nodes:
                nodes[key] = {
                    "id": key,
                    "code": code_val,
                    "label": label[:80] if label else code_val,
                    "type": code_type,
                    "category": category or "",
                }
            return key

        def add_edge(source_key, target_key, relationship):
            edges.append({"source": source_key, "target": target_key, "relationship": relationship})

        try:
            root_type = None

            # SNOMED root
            snomed = session.query(SnomedCode).filter_by(code=code).first()
            if snomed:
                root_type = "SNOMED"
                root_key = add_node(snomed.code, snomed.description, "SNOMED", snomed.semantic_tag or "")
                
                # ICD-10 mappings
                for m in session.execute(
                    snomed_icd10_mapping.select().where(snomed_icd10_mapping.c.snomed_code == code)
                ).fetchall():
                    icd10 = session.query(ICD10Code).filter_by(code=m.icd10_code).first()
                    if icd10:
                        icd_key = add_node(icd10.code, icd10.description, "ICD-10-CM", icd10.chapter or "")
                        add_edge(root_key, icd_key, "maps_to")
                        for hm in session.execute(
                            icd10_hcc_mapping.select().where(icd10_hcc_mapping.c.icd10_code == icd10.code)
                        ).fetchall():
                            hcc = session.query(HCCCode).filter_by(code=hm.hcc_code).first()
                            if hcc:
                                hcc_key = add_node(hcc.code, hcc.description, "HCC", hcc.category or "")
                                add_edge(icd_key, hcc_key, "risk_adjusts_to")
                
                # RxNorm mappings
                for m in session.execute(
                    rxnorm_snomed_mapping.select().where(rxnorm_snomed_mapping.c.snomed_code == code)
                ).fetchall()[:25]:
                    rxnorm_obj = session.query(RxNormCode).filter_by(code=m.rxnorm_code).first()
                    if rxnorm_obj:
                        rxnorm_key = add_node(rxnorm_obj.code, rxnorm_obj.name, "RxNorm", rxnorm_obj.term_type or "")
                        add_edge(root_key, rxnorm_key, "cross_reference")
                        # Add NDC mappings from RxNorm
                        for ndc_m in session.execute(
                            ndc_rxnorm_mapping.select().where(ndc_rxnorm_mapping.c.rxnorm_code == rxnorm_obj.code)
                        ).fetchall()[:10]:
                            ndc_obj = session.query(NDCCode).filter_by(code=ndc_m.ndc_code).first()
                            if ndc_obj:
                                ndc_key = add_node(ndc_obj.code, ndc_obj.product_name, "NDC", ndc_obj.product_type or "")
                                add_edge(rxnorm_key, ndc_key, "standardized_as")

            # ICD-10 root
            icd10 = session.query(ICD10Code).filter_by(code=code).first()
            if icd10 and root_type is None:
                root_type = "ICD-10-CM"
                root_key = add_node(icd10.code, icd10.description, "ICD-10-CM", icd10.chapter or "")
                for hm in session.execute(
                    icd10_hcc_mapping.select().where(icd10_hcc_mapping.c.icd10_code == code)
                ).fetchall():
                    hcc = session.query(HCCCode).filter_by(code=hm.hcc_code).first()
                    if hcc:
                        hcc_key = add_node(hcc.code, hcc.description, "HCC", hcc.category or "")
                        add_edge(root_key, hcc_key, "risk_adjusts_to")
                for m in session.execute(
                    snomed_icd10_mapping.select().where(snomed_icd10_mapping.c.icd10_code == code)
                ).fetchall():
                    snomed_obj = session.query(SnomedCode).filter_by(code=m.snomed_code).first()
                    if snomed_obj:
                        s_key = add_node(snomed_obj.code, snomed_obj.description, "SNOMED", snomed_obj.semantic_tag or "")
                        add_edge(s_key, root_key, "maps_to")

            # HCC root
            hcc = session.query(HCCCode).filter_by(code=code).first()
            if hcc and root_type is None:
                root_type = "HCC"
                root_key = add_node(hcc.code, hcc.description, "HCC", hcc.category or "")
                for hm in session.execute(
                    icd10_hcc_mapping.select().where(icd10_hcc_mapping.c.hcc_code == code)
                ).fetchall()[:50]:
                    icd10_obj = session.query(ICD10Code).filter_by(code=hm.icd10_code).first()
                    if icd10_obj:
                        icd_key = add_node(icd10_obj.code, icd10_obj.description, "ICD-10-CM", icd10_obj.chapter or "")
                        add_edge(icd_key, root_key, "risk_adjusts_to")

            # RxNorm root
            rxnorm = session.query(RxNormCode).filter_by(code=code).first()
            if rxnorm and root_type is None:
                root_type = "RxNorm"
                root_key = add_node(rxnorm.code, rxnorm.name, "RxNorm", rxnorm.term_type or "")
                for m in session.execute(
                    rxnorm_snomed_mapping.select().where(rxnorm_snomed_mapping.c.rxnorm_code == code)
                ).fetchall()[:25]:
                    snomed_obj = session.query(SnomedCode).filter_by(code=m.snomed_code).first()
                    if snomed_obj:
                        s_key = add_node(snomed_obj.code, snomed_obj.description, "SNOMED", snomed_obj.semantic_tag or "")
                        add_edge(root_key, s_key, "cross_reference")
                for m in session.execute(
                    ndc_rxnorm_mapping.select().where(ndc_rxnorm_mapping.c.rxnorm_code == code)
                ).fetchall()[:25]:
                    ndc_obj = session.query(NDCCode).filter_by(code=m.ndc_code).first()
                    if ndc_obj:
                        ndc_key = add_node(ndc_obj.code, ndc_obj.product_name, "NDC", ndc_obj.product_type or "")
                        add_edge(ndc_key, root_key, "standardized_as")

            # NDC root
            ndc = session.query(NDCCode).filter_by(code=code).first()
            if ndc and root_type is None:
                root_type = "NDC"
                root_key = add_node(ndc.code, ndc.product_name, "NDC", ndc.product_type or "")
                for m in session.execute(
                    ndc_rxnorm_mapping.select().where(ndc_rxnorm_mapping.c.ndc_code == code)
                ).fetchall()[:25]:
                    rxnorm_obj = session.query(RxNormCode).filter_by(code=m.rxnorm_code).first()
                    if rxnorm_obj:
                        rxnorm_key = add_node(rxnorm_obj.code, rxnorm_obj.name, "RxNorm", rxnorm_obj.term_type or "")
                        add_edge(root_key, rxnorm_key, "standardized_as")

            if root_type is None:
                return None

            return {"root": f"{root_type}:{code}", "nodes": list(nodes.values()), "edges": edges}
        finally:
            session.close()
