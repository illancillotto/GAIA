"""GAIA Organigramma module — canonical organizational structure layer.

Layer CANONICO (org_unit / org_assignment / org_visibility_override) come verità
principale, con BRIDGE verso le sorgenti WhiteCompany (wc_area / wc_operator /
wc_org_chart_entry) e verso la vecchia tabella operazioni.team tramite
org_source_link. WhiteCompany resta SORGENTE, non verità: la provenienza è
etichettata e gli override manuali non vengono mai sovrascritti dal sync.
"""
