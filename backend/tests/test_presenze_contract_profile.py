from app.modules.presenze.services.contract_profile import (
    infer_contract_profile_from_schedule_codes,
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

    # Minuti impostati a mano senza tipo contratto: i minuti restano quelli di HR ma il
    # tipo viene comunque dedotto, altrimenti il collaboratore non entra nelle regole.
    partial = resolve_contract_profile(None, 390, template_code="IMP1_STD")
    assert partial.contract_kind == "impiegato"
    assert partial.standard_daily_minutes == 390

    unknown = resolve_contract_profile(None, 390, template_code="TEMPLATE_SCONOSCIUTO")
    assert unknown.contract_kind is None
    assert unknown.standard_daily_minutes == 390

    invalid_explicit = resolve_contract_profile("DIRIGENTE", None, template_code="IMP1_STD")
    assert invalid_explicit.contract_kind == "impiegato"
    assert invalid_explicit.standard_daily_minutes == 385


def test_infer_contract_profile_from_template_code_covers_the_impianti_and_shift_codes() -> None:
    for code in ("OPSABE", "OPFSABE", "OPESAB", "ADD_10", "ADD_SM", "IRRSE_2", "IRRMA"):
        profile = infer_contract_profile_from_template_code(code)
        assert profile.contract_kind == "operaio", code
        assert profile.standard_daily_minutes == 420, code

    telecontrollo = infer_contract_profile_from_template_code("TELEC_3")
    assert telecontrollo.contract_kind == "impiegato"
    assert telecontrollo.standard_daily_minutes == 480

    for code in ("DOM", "SAB", "FESTIVO", "RIPTURN", "SMONTO", "CBO_- 1 ora"):
        assert infer_contract_profile_from_template_code(code).contract_kind is None, code


def test_infer_contract_profile_from_schedule_codes_uses_the_prevailing_code() -> None:
    # Operaio turnista: TELEC solo nei giorni di turno, OPE0714 nei giorni ordinari.
    turnista = infer_contract_profile_from_schedule_codes(
        ["DOM", "SAB", "TELEC_1", "TELEC_2", "OPE0714", "OPE0714", "OPESAB"]
    )
    assert turnista.contract_kind == "operaio"
    assert turnista.standard_daily_minutes == 420

    # Il codice ordinario prevale su quello di sabato anche se il sabato viene prima.
    assert infer_contract_profile_from_schedule_codes(
        ["OPESAB", "OPE0736", "OPE0736"]
    ).standard_daily_minutes == 456

    assert infer_contract_profile_from_schedule_codes(["DOM", "IMP1", "RIENTRO IMP"]).contract_kind == "impiegato"
    assert infer_contract_profile_from_schedule_codes(["TELEC_1", "DOM"]).contract_kind == "impiegato"
    assert infer_contract_profile_from_schedule_codes(["DOM", "SAB", None, "  "]).contract_kind is None
    assert infer_contract_profile_from_schedule_codes([]).contract_kind is None


def test_resolve_contract_profile_falls_back_to_schedule_codes_without_a_template() -> None:
    inferred = resolve_contract_profile(None, None, schedule_codes=["DOM", "OPE0714", "OPE0714"])
    assert inferred.contract_kind == "operaio"
    assert inferred.standard_daily_minutes == 420

    # Il template assegnato resta prioritario sui codici giornalieri.
    from_template = resolve_contract_profile(
        None, None, template_code="IMP1_STD", schedule_codes=["OPE0714", "OPE0714"]
    )
    assert from_template.contract_kind == "impiegato"

    # Un template sconosciuto non blocca il fallback sui codici giornalieri.
    from_codes = resolve_contract_profile(
        None, None, template_code="TEMPLATE_SCONOSCIUTO", schedule_codes=["ADD_10", "ADD_10"]
    )
    assert from_codes.contract_kind == "operaio"

    assert resolve_contract_profile("impiegato", None, schedule_codes=["OPE0714"]).contract_kind == "impiegato"
    assert resolve_contract_profile(None, None, schedule_codes=None).contract_kind is None
