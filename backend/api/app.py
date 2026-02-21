"""
Flask API for the Coding Manager application.

Provides REST endpoints for:
- Searching codes across all coding sets
- Retrieving code details
- Viewing mappings between coding sets (SNOMED <-> ICD-10-CM <-> HCC)
- Comparing coding sets
- Accessing coding resources/guidelines

All business logic is delegated to the service layer under ``services/``.
"""

import os
import sys

from flask import Flask, jsonify, request
from flask_cors import CORS

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.models import init_db
from api.services import CodingService, MappingService, ConflictService

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize database on startup
init_db()


# ─── Health Check ────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "Coding Manager API"})


# ─── Autocomplete ────────────────────────────────────────────────────────────

@app.route("/api/autocomplete", methods=["GET"])
def autocomplete():
    q = request.args.get("q", "").strip()
    code_type = request.args.get("type", "").lower()
    if len(q) < 2:
        return jsonify([])
    return jsonify(CodingService.autocomplete(q, code_type))


# ─── Mapping Graph ───────────────────────────────────────────────────────────

@app.route("/api/mappings/graph/<code>", methods=["GET"])
def get_mapping_graph(code):
    result = MappingService.get_mapping_graph(code)
    if result is None:
        return jsonify({"error": f"Code {code} not found"}), 404
    return jsonify(result)


# ─── Global Search ───────────────────────────────────────────────────────────

@app.route("/api/search", methods=["GET"])
def search_codes():
    q = request.args.get("q", "").strip()
    code_type = request.args.get("type", "").lower()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))
    if not q:
        return jsonify({"error": "Search query 'q' is required"}), 400
    return jsonify(CodingService.search(q, code_type, page, per_page))


# ─── SNOMED ──────────────────────────────────────────────────────────────────

@app.route("/api/snomed", methods=["GET"])
def list_snomed_codes():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))
    q = request.args.get("q", "").strip()
    return jsonify(CodingService.list_snomed(page, per_page, q))


@app.route("/api/snomed/<code>", methods=["GET"])
def get_snomed_code(code):
    result = MappingService.get_snomed_detail(code)
    if result is None:
        return jsonify({"error": f"SNOMED code {code} not found"}), 404
    return jsonify(result)


# ─── ICD-10-CM ───────────────────────────────────────────────────────────────

@app.route("/api/icd10", methods=["GET"])
def list_icd10_codes():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))
    q = request.args.get("q", "").strip()
    return jsonify(CodingService.list_icd10(page, per_page, q))


@app.route("/api/icd10/hierarchy", methods=["GET"])
def list_icd10_hierarchy():
    letter = request.args.get("letter", "").strip()
    q = request.args.get("q", "").strip()
    return jsonify(CodingService.list_icd10_hierarchy(letter, q))


@app.route("/api/icd10/hierarchy/children/<code>", methods=["GET"])
def get_icd10_category_children(code):
    return jsonify(CodingService.get_icd10_category_children(code))


@app.route("/api/icd10/<code>", methods=["GET"])
def get_icd10_code(code):
    result = MappingService.get_icd10_detail(code)
    if result is None:
        return jsonify({"error": f"ICD-10 code {code} not found"}), 404
    return jsonify(result)


# ─── HCC ─────────────────────────────────────────────────────────────────────

@app.route("/api/hcc", methods=["GET"])
def list_hcc_codes():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))
    q = request.args.get("q", "").strip()
    return jsonify(CodingService.list_hcc(page, per_page, q))


@app.route("/api/hcc/<code>", methods=["GET"])
def get_hcc_code(code):
    result = MappingService.get_hcc_detail(code)
    if result is None:
        return jsonify({"error": f"HCC code {code} not found"}), 404
    return jsonify(result)


# ─── CPT ─────────────────────────────────────────────────────────────────────

@app.route("/api/cpt", methods=["GET"])
def list_cpt_codes():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))
    q = request.args.get("q", "").strip()
    dhs_only = request.args.get("dhs", "").lower() in ("true", "1", "yes")
    return jsonify(CodingService.list_cpt(page, per_page, q, dhs_only))


@app.route("/api/cpt/<code>", methods=["GET"])
def get_cpt_code(code):
    result = MappingService.get_cpt_detail(code)
    if result is None:
        return jsonify({"error": f"CPT code {code} not found"}), 404
    return jsonify(result)


# ─── HCPCS ───────────────────────────────────────────────────────────────────

@app.route("/api/hcpcs", methods=["GET"])
def list_hcpcs_codes():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))
    q = request.args.get("q", "").strip()
    dhs_only = request.args.get("dhs", "").lower() in ("true", "1", "yes")
    return jsonify(CodingService.list_hcpcs(page, per_page, q, dhs_only))


@app.route("/api/hcpcs/<code>", methods=["GET"])
def get_hcpcs_code(code):
    result = MappingService.get_hcpcs_detail(code)
    if result is None:
        return jsonify({"error": f"HCPCS code {code} not found"}), 404
    return jsonify(result)


# ─── CPT / DHS Categories (Designated Health Services) ──────────────────────────────

@app.route("/api/dhs", methods=["GET"])
def list_dhs_codes():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    category = request.args.get("category", "").strip()
    return jsonify(CodingService.list_dhs(page, per_page, category))


@app.route("/api/dhs/categories", methods=["GET"])
def list_dhs_categories():
    return jsonify(CodingService.list_dhs_categories())


# ─── RxNorm ──────────────────────────────────────────────────────────────────

@app.route("/api/rxnorm", methods=["GET"])
def list_rxnorm_codes():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))
    q = request.args.get("q", "").strip()
    return jsonify(CodingService.list_rxnorm(page, per_page, q))


@app.route("/api/rxnorm/<code>", methods=["GET"])
def get_rxnorm_code(code):
    result = MappingService.get_rxnorm_detail(code)
    if result is None:
        return jsonify({"error": f"RxNorm code {code} not found"}), 404
    return jsonify(result)


# ─── NDC ────────────────────────────────────────────────────────────────────

@app.route("/api/ndc", methods=["GET"])
def list_ndc_codes():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))
    q = request.args.get("q", "").strip()
    return jsonify(CodingService.list_ndc(page, per_page, q))


@app.route("/api/ndc/<code>", methods=["GET"])
def get_ndc_code(code):
    result = MappingService.get_ndc_detail(code)
    if result is None:
        return jsonify({"error": f"NDC code {code} not found"}), 404
    return jsonify(result)


# ─── Directional Mappings ────────────────────────────────────────────────────

@app.route("/api/mappings/snomed-to-icd10/<snomed_code>", methods=["GET"])
def get_snomed_to_icd10(snomed_code):
    return jsonify(MappingService.snomed_to_icd10(snomed_code))


@app.route("/api/mappings/snomed-to-hcc/<snomed_code>", methods=["GET"])
def get_snomed_to_hcc(snomed_code):
    return jsonify(MappingService.snomed_to_hcc(snomed_code))


@app.route("/api/mappings/rxnorm-to-snomed/<rxnorm_code>", methods=["GET"])
def get_rxnorm_to_snomed(rxnorm_code):
    return jsonify(MappingService.rxnorm_to_snomed(rxnorm_code))


@app.route("/api/mappings/ndc-to-rxnorm/<ndc_code>", methods=["GET"])
def get_ndc_to_rxnorm(ndc_code):
    return jsonify(MappingService.ndc_to_rxnorm(ndc_code))


@app.route("/api/mappings/rxnorm-to-ndc/<rxnorm_code>", methods=["GET"])
def get_rxnorm_to_ndc(rxnorm_code):
    return jsonify(MappingService.rxnorm_to_ndc(rxnorm_code))


@app.route("/api/mappings/icd10-to-hcc/<icd10_code>", methods=["GET"])
def get_icd10_to_hcc(icd10_code):
    return jsonify(MappingService.icd10_to_hcc(icd10_code))


# ─── Compare ─────────────────────────────────────────────────────────────────

@app.route("/api/compare", methods=["GET"])
def compare_codes():
    codes_param = request.args.get("codes", "")
    if not codes_param:
        return jsonify({"error": "Parameter 'codes' is required"}), 400
    codes = [c.strip() for c in codes_param.split(",")]
    results = CodingService.compare(codes)
    return jsonify({"codes": results, "total": len(results)})


# ─── Statistics ──────────────────────────────────────────────────────────────

@app.route("/api/stats", methods=["GET"])
def get_statistics():
    return jsonify(CodingService.get_stats())


# ─── Resources ───────────────────────────────────────────────────────────────

@app.route("/api/resources", methods=["GET"])
def get_resources():
    return jsonify(CodingService.get_resources())


# ─── Conflicts ───────────────────────────────────────────────────────────────

@app.route("/api/conflicts", methods=["GET"])
def get_conflicts():
    return jsonify(ConflictService.list_conflicts(
        page=request.args.get("page", 1, type=int),
        per_page=request.args.get("per_page", 25, type=int),
        status=request.args.get("status"),
        source_system=request.args.get("source_system"),
        target_system=request.args.get("target_system"),
        reason=request.args.get("reason"),
        search=request.args.get("q", "").strip(),
    ))


@app.route("/api/conflicts/stats", methods=["GET"])
def get_conflict_stats():
    return jsonify(ConflictService.get_stats())


@app.route("/api/conflicts/<int:conflict_id>", methods=["GET"])
def get_conflict(conflict_id):
    result = ConflictService.get_conflict(conflict_id)
    if result is None:
        return jsonify({"error": "Conflict not found"}), 404
    return jsonify(result)


@app.route("/api/conflicts/<int:conflict_id>", methods=["PATCH"])
def update_conflict(conflict_id):
    data = request.get_json()
    try:
        result = ConflictService.update_conflict(
            conflict_id,
            action=data.get("action", ""),
            resolution=data.get("resolution", ""),
            resolved_code=data.get("resolved_code", ""),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if result is None:
        return jsonify({"error": "Conflict not found"}), 404
    return jsonify(result)


@app.route("/api/conflicts/bulk", methods=["PATCH"])
def bulk_update_conflicts():
    data = request.get_json()
    try:
        updated = ConflictService.bulk_update(
            ids=data.get("ids", []),
            action=data.get("action", ""),
            resolution=data.get("resolution", ""),
            resolved_code=data.get("resolved_code", ""),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"updated": updated})


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
