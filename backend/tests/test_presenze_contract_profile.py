from app.modules.presenze.services.contract_profile import (
    infer_contract_profile_from_template_code,
    normalize_contract_kind,
    normalize_operai_group,
    resolve_contract_profile,
)


def test_normalize_contract_kind_accepts_supported_values_only() -> None:
    assert normalize_contract_kind(" OPERAIO ") == "operaio"
    assert normalize_contract_kind("impiegato") == "impiegato"
    assert normalize_contract_kind(" Quadro ") == "quadro"
    assert normalize_contract_kind("ALTRO") == "altro"
    assert normalize_contract_kind("") is None
    assert normalize_contract_kind("dirigente") is None
    assert normalize_contract_kind(None) is None

    assert normalize_operai_group(" AGRARIO ") == "agrario"
    assert normalize_operai_group("catasto_magazzino") == "catasto_magazzino"
    assert normalize_operai_group(None) is None
    assert normalize_operai_group("") is None
    assert normalize_operai_group("altro") is None


def test_infer_contract_profile_from_template_code_maps_known_templates() -> None:
    assert infer_contract_profile_from_template_code("OPE0736_STD").contract_kind == "operaio"
    assert infer_contract_profile_from_template_code("OPE0736_STD").standard_daily_minutes == 456

    assert infer_contract_profile_from_template_code(" OPE0714_1E3SAB ").contract_kind == "operaio"
    assert infer_contract_profile_from_template_code(" OPE0714_1E3SAB ").standard_daily_minutes == 420
    assert infer_contract_profile_from_template_code("OP_5.3_12.3").contract_kind == "operaio"
    assert infer_contract_profile_from_template_code("OP_5.3_12.3").standard_daily_minutes == 420
    assert infer_contract_profile_from_template_code("OSAB5.3_12.3").contract_kind == "operaio"
    assert infer_contract_profile_from_template_code("OSAB5.3_12.3").standard_daily_minutes == 420

    assert infer_contract_profile_from_template_code("RIENTRO IMP").contract_kind == "impiegato"
    assert infer_contract_profile_from_template_code("RIENTRO IMP").standard_daily_minutes == 385
    assert infer_contract_profile_from_template_code("IMP1_STD").contract_kind == "impiegato"
    assert infer_contract_profile_from_template_code("IMP1_STD").standard_daily_minutes == 385

    assert infer_contract_profile_from_template_code("UNKNOWN").contract_kind is None
    assert infer_contract_profile_from_template_code("UNKNOWN").standard_daily_minutes is None
    assert infer_contract_profile_from_template_code("   ").contract_kind is None
    assert infer_contract_profile_from_template_code("   ").standard_daily_minutes is None
    assert infer_contract_profile_from_template_code(None).contract_kind is None


def test_resolve_contract_profile_prefers_explicit_values_over_template_inference() -> None:
    explicit = resolve_contract_profile("Impiegato", 385, template_code="OPE0714_1E3SAB")
    assert explicit.contract_kind == "impiegato"
    assert explicit.standard_daily_minutes == 385

    inferred = resolve_contract_profile(None, None, template_code="OPE0714_1E3SAB")
    assert inferred.contract_kind == "operaio"
    assert inferred.standard_daily_minutes == 420

    partial = resolve_contract_profile(None, 390, template_code="IMP1_STD")
    assert partial.contract_kind is None
    assert partial.standard_daily_minutes == 390

    invalid_explicit = resolve_contract_profile("DIRIGENTE", None, template_code="IMP1_STD")
    assert invalid_explicit.contract_kind == "impiegato"
    assert invalid_explicit.standard_daily_minutes == 385
