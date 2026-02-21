"""
NDC (National Drug Code) Loader

Reads the FDA NDC text file (pipe-delimited) from staging/ndc/ndctext.zip.
The file typically contains product and package NDC codes with product information.
"""

import os
import re
import logging
import zipfile
from typing import Set

from pipeline.base import BaseLoader
from pipeline.helpers import bulk_insert_ignore, STAGING_DIR, BATCH_SIZE, find_zip

logger = logging.getLogger(__name__)


def normalize_ndc(ndc: str) -> str:
    """Normalize NDC code to 11-digit format (no dashes, leading zeros).
    
    NDC codes can be in formats:
    - 5-4-2 (labeler-product-package)
    - 4-4-2
    - 5-3-2
    - 11 digits (no dashes)
    """
    if not ndc:
        return ""
    # Remove dashes and spaces
    ndc = ndc.replace("-", "").replace(" ", "").strip()
    # Pad to 11 digits if needed
    if len(ndc) < 11:
        ndc = ndc.zfill(11)
    elif len(ndc) > 11:
        ndc = ndc[:11]
    return ndc


def format_ndc_display(ndc: str) -> str:
    """Format 11-digit NDC as 5-4-2 for display."""
    if len(ndc) == 11:
        return f"{ndc[:5]}-{ndc[5:9]}-{ndc[9:]}"
    return ndc


class NDCLoader(BaseLoader):
    system_name = "NDC"
    model_class = None  # Set below after import

    def _load_from_source(self, session) -> int:
        ndc_dir = os.path.join(STAGING_DIR, "ndc")
        if not os.path.exists(ndc_dir):
            return 0

        zip_path = find_zip("ndctext")
        if not zip_path:
            logger.warning("No ndctext.zip file found in staging/ndc/")
            return 0

        return self._parse_ndc_file(session, zip_path)

    def _parse_ndc_file(self, session, zip_path: str) -> int:
        """Parse FDA NDC pipe-delimited text file."""
        from pipeline.models import NDCCode
        
        count = 0
        batch = []
        seen_codes: Set[str] = set()

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Prefer product.txt over package.txt
                txt_entries = [n for n in zf.namelist() if n.lower().endswith(".txt")]
                if not txt_entries:
                    logger.warning("No .txt file found in NDC zip")
                    return 0

                # Prefer product.txt, fallback to first .txt file
                product_file = next((n for n in txt_entries if "product" in n.lower()), None)
                txt_file = product_file if product_file else txt_entries[0]
                logger.info(f"  Parsing {txt_file} from {os.path.basename(zip_path)}")

                with zf.open(txt_file) as f:
                    # Read header to determine column positions
                    # NDC files are tab-delimited
                    header_line = f.readline().decode("utf-8", errors="ignore").strip()
                    # Try tab first, then pipe as fallback
                    delimiter = "\t" if "\t" in header_line else "|"
                    headers = [h.strip().lower() for h in header_line.split(delimiter)]
                    
                    # Map common NDC file column names
                    col_map = {}
                    for i, h in enumerate(headers):
                        h_lower = h.lower()
                        if "productndc" in h_lower or "product_ndc" in h_lower:
                            col_map["product_ndc"] = i
                        elif "packagendc" in h_lower or "package_ndc" in h_lower:
                            col_map["package_ndc"] = i
                        elif "productname" in h_lower or "product_name" in h_lower:
                            col_map["product_name"] = i
                        elif "proprietaryname" in h_lower or "proprietary_name" in h_lower:
                            col_map["proprietary_name"] = i
                        elif "nonproprietaryname" in h_lower or "non_proprietary_name" in h_lower:
                            col_map["non_proprietary_name"] = i
                        elif "dosageform" in h_lower or "dosage_form" in h_lower:
                            col_map["dosage_form"] = i
                        elif "route" in h_lower:
                            col_map["route"] = i
                        elif "strength" in h_lower:
                            col_map["strength"] = i
                        elif "activeingredient" in h_lower or "active_ingredient" in h_lower:
                            col_map["active_ingredient"] = i
                        elif "producttype" in h_lower or "product_type" in h_lower:
                            col_map["product_type"] = i
                        elif "marketingcategory" in h_lower or "marketing_category" in h_lower:
                            col_map["marketing_category"] = i
                        elif "applicationnumber" in h_lower or "application_number" in h_lower:
                            col_map["application_number"] = i
                        elif "labelername" in h_lower or "labeler_name" in h_lower:
                            col_map["labeler_name"] = i
                        elif "listingrecord" in h_lower or "listing_record" in h_lower:
                            col_map["listing_record"] = i
                        elif "deaschedule" in h_lower or "dea_schedule" in h_lower:
                            col_map["dea_schedule"] = i
                        elif "ndcexcludeflag" in h_lower or "ndc_exclude_flag" in h_lower:
                            col_map["ndc_exclude_flag"] = i

                    # Process data rows
                    for line_num, line_bytes in enumerate(f, start=2):
                        try:
                            line = line_bytes.decode("utf-8", errors="ignore").strip()
                            if not line:
                                continue
                            
                            # Use same delimiter as header
                            fields = line.split(delimiter)
                            if len(fields) < len(headers):
                                continue

                            # Get package NDC (preferred) or product NDC
                            package_ndc = ""
                            product_ndc = ""
                            
                            if "package_ndc" in col_map:
                                package_ndc = fields[col_map["package_ndc"]].strip()
                            if "product_ndc" in col_map:
                                product_ndc = fields[col_map["product_ndc"]].strip()
                            
                            # Use package NDC as primary code, fallback to product NDC
                            primary_ndc = normalize_ndc(package_ndc) if package_ndc else normalize_ndc(product_ndc)
                            if not primary_ndc or len(primary_ndc) != 11:
                                continue
                            
                            if primary_ndc in seen_codes:
                                continue
                            seen_codes.add(primary_ndc)

                            # Extract fields
                            proprietary_name = fields[col_map.get("proprietary_name", 0)].strip() if "proprietary_name" in col_map else ""
                            non_proprietary_name = fields[col_map.get("non_proprietary_name", 0)].strip() if "non_proprietary_name" in col_map else ""
                            # Use proprietary name as product_name, fallback to non-proprietary
                            product_name = proprietary_name or non_proprietary_name
                            if not product_name:
                                continue  # Skip rows without product name

                            dosage_form = fields[col_map.get("dosage_form", 0)].strip() if "dosage_form" in col_map else ""
                            route = fields[col_map.get("route", 0)].strip() if "route" in col_map else ""
                            # Combine active ingredient numerator and unit for strength
                            active_numerator = fields[col_map.get("active_numerator_strength", 0)].strip() if "active_numerator_strength" in col_map else ""
                            active_unit = fields[col_map.get("active_ing_unit", 0)].strip() if "active_ing_unit" in col_map else ""
                            strength = f"{active_numerator} {active_unit}".strip() if active_numerator and active_unit else ""
                            
                            active_ingredient = fields[col_map.get("substancename", 0)].strip() if "substancename" in col_map else ""
                            
                            product_type = fields[col_map.get("product_type", 0)].strip() if "product_type" in col_map else ""
                            marketing_category = fields[col_map.get("marketing_category", 0)].strip() if "marketing_category" in col_map else ""
                            application_number = fields[col_map.get("application_number", 0)].strip() if "application_number" in col_map else ""
                            labeler_name = fields[col_map.get("labeler_name", 0)].strip()[:500] if "labeler_name" in col_map else ""
                            listing_record = fields[col_map.get("listing_record", 0)].strip() if "listing_record" in col_map else ""
                            dea_schedule = fields[col_map.get("dea_schedule", 0)].strip() if "dea_schedule" in col_map else ""
                            ndc_exclude_flag = fields[col_map.get("ndc_exclude_flag", 0)].strip() if "ndc_exclude_flag" in col_map else ""

                            # Format NDC codes
                            formatted_product_ndc = format_ndc_display(normalize_ndc(product_ndc)) if product_ndc else ""
                            formatted_package_ndc = format_ndc_display(normalize_ndc(package_ndc)) if package_ndc else ""
                            
                            # Use product NDC as primary code, fallback to package NDC
                            primary_code = normalize_ndc(product_ndc) if product_ndc else normalize_ndc(package_ndc)
                            if not primary_code or len(primary_code) != 11:
                                continue

                            batch.append(NDCCode(
                                code=primary_code,  # Store as 11-digit without dashes
                                product_ndc=formatted_product_ndc,
                                package_ndc=formatted_package_ndc,
                                product_name=product_name[:1000],
                                proprietary_name=proprietary_name[:500] if proprietary_name else None,
                                non_proprietary_name=non_proprietary_name[:500] if non_proprietary_name else None,
                                dosage_form=dosage_form[:200] if dosage_form else None,
                                route=route[:200] if route else None,
                                strength=strength[:200] if strength else None,
                                active_ingredient=active_ingredient[:1000] if active_ingredient else None,
                                product_type=product_type[:50] if product_type else None,
                                marketing_category=marketing_category[:100] if marketing_category else None,
                                application_number=application_number[:50] if application_number else None,
                                labeler_name=labeler_name[:500] if labeler_name else None,
                                listing_record_certified_through=listing_record[:20] if listing_record else None,
                                dea_schedule=dea_schedule[:10] if dea_schedule else None,
                                ndc_exclude_flag=ndc_exclude_flag[:10] if ndc_exclude_flag else None,
                                active=ndc_exclude_flag.upper() != "Y" if ndc_exclude_flag else True,
                            ))
                            count += 1

                            if len(batch) >= BATCH_SIZE:
                                bulk_insert_ignore(session, NDCCode, batch)
                                batch.clear()
                                logger.info(f"  Processed {count:,} NDC codes...")

                        except Exception as e:
                            if line_num < 10:  # Only log first few errors
                                logger.warning(f"  Error parsing line {line_num}: {e}")

                if batch:
                    bulk_insert_ignore(session, NDCCode, batch)
                    session.flush()

                logger.info(f"  Parsed {count:,} unique NDC codes from {txt_file}")

        except Exception as e:
            logger.warning(f"Error parsing NDC file {zip_path}: {e}")
            import traceback
            traceback.print_exc()

        return count
