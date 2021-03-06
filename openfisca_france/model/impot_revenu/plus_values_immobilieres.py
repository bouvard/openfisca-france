# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014, 2015 OpenFisca Team
# https://github.com/openfisca
#
# This file is part of OpenFisca.
#
# OpenFisca is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# OpenFisca is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from numpy import maximum as max_, minimum as min_

from ..base import *  # noqa analysis:ignore


########################################################################
#  Calcul de l'impôt sur les plus-values immobilières
# Impôt sur le revenu afférent à la plus-value immobilière (CGI, art. 150 U, 150 UC-I et 150 UD)
# Prélèvement dû par les non-résidents assujettis ou non à l’impôt sur le revenu (CGI, art. 244 bis A)
# Taxe forfaitaire sur la cession de terrains nus devenus constructibles (CGI, art. 1529)
# Taxe sur la cession à titre onéreux de terrains nus rendus constructibles (CGI, art.1605 nonies)
# 2048-IMM-SD
########################################################################
#TODO: create new function for f3VV (new legislation : non-resident_45%)

def _plus_value_brute(prix_pv_immo, charges_pv_immo, frais_pv_immo, prix_acqu_immo,
                      charges_aqu_immo, frais_acqu_immo, const_acqu_immo, voirie_acqu_immo):
    """
    Calcul de la plus-value immobilière brute
    """
    # CESSION
    prix_cess_immo = 0    # 10;  PRIX DE CESSION OU INDEMNITE D’EXPROPRIATION = €
    charges_cess_immo = 0 # 11. CHARGES ET INDEMNITES SUPPORTEES PAR L’ACQUEREUR + €
    frais_cess_immo =0    # 12. FRAIS ET TAXES SUPPORTES PAR LE VENDEUR (NOTAMMENT FRAIS DE REPRESENTATION FISCALE) - €

    # 13. PRIX DE CESSION CORRIGE (LIGNE 10 + LIGNE 11 – LIGNE 12) = = €
    prix_cess_corr = prix_cess_immo + charges_cess_immo - frais_cess_immo

    # ACQISISTION
    prix_acqu_immo = 0   # 20. PRIX D’ACQUISITION OU VALEUR VENALE = €
    charges_aqu_immo = 0 # 21. CHARGES ET INDEMNITES (MONTANT REEL) + €
    frais_acqu_immo = 0  # 22. FRAIS D’ACQUISITION :
                         # * A TITRE GRATUIT (MONTANT REEL) + €
                         # * A TITRE ONEREUX (MONTANT REEL OU FIXE A 7,5% DU PRIX D’ACQUISITION) + €
    const_acqu_immo = 0  # 23. DEPENSES DE CONSTRUCTION, RECONSTRUCTION, AGRANDISSEMENT OU AMELIORATION + €
                         # (MONTANT REEL OU FIXE A 15% DU PRIX D’ACQUISITION SI IMMEUBLE BATI DETENU DEPUIS PLUS DE 5 ANS).
    voirie_acqu_immo = 0 # 24. FRAIS DE VOIRIE, RESEAUX ET DISTRIBUTION + €
    valeur_venale  = prix_acqu_immo + charges_aqu_immo + frais_acqu_immo + const_acqu_immo + voirie_acqu_immo # 25. PRIX D’ACQUISITION OU VALEUR VENALE CORRIGE (LIGNE 20 + LIGNE 21 + LIGNE 22 + LIGNE 23 + LIGNE 24) = - €
    return prix_cess_corr-valeur_venale


def _plus_value_nette(period, plus_value_brute, dur_det_immo, pv_immo = law.ir.pv_immo):
    """
    Calcul de la plus value immobilière nette
    """
    # 40. ABATTEMENT POUR DUREE DE DETENTION
    # 41. NOMBRE D’ANNEES DE DETENTION AU-DELA DE LA 5EME ANNEE
    if period.start:  # TODO:
        taux_reduc = max_(dur_det_immo - pv_immo.ann_det1, 0) * pv_immo.taux1
    else:
        taux_reduc = (max_(dur_det_immo - pv_immo.ann_det3, 0) * pv_immo.taux3
            + max_(min_(dur_det_immo, pv_immo.ann_det3) - pv_immo.ann_det2, 0) * pv_immo.taux2
            + max_(min_(dur_det_immo, pv_immo.ann_det2) - pv_immo.ann_det1, 0) * pv_immo.taux1)

    taux_reduc = min_(taux_reduc, 1.0)
    pv_impos = (1 - taux_reduc) * plus_value_brute

    # 45. MONTANT DE LA PLUS-VALUE BENEFICIANT, SOUS CONDITIONS, DE L’EXONERATION AU TITRE DE LA
    # PREMIERE CESSION D’UN LOGEMENT EN VUE DE L’ACQUISITION DE LA RESIDENCE PRINCIPALE
    # (CGI, 1° BIS DU II DE L’ARTICLE 150 U) TODO:
    exo = 0

    pv_net_impos = max_(pv_impos - exo, 0)  # 46. PLUS-VALUE NETTE IMPOSABLE [LIGNE 44 OU (LIGNE 44 – LIGNE 45)] = €
    # 50. PLUS-VALUE NETTE IMPOSABLE GLOBALE =
    # (LIGNE 46 OU TOTAL DES LIGNES 46 SI PLUSIEURS 2048-IMM-SD PAGE 2)

    # Lorsqu’une même cession porte sur des biens pour lesquels sont prévues des règles différentes (acquisitions
    # successives de fractions divises ou indivises notamment), il convient de remplir les lignes 10 à 46 pour chacune
    # des fractions (utiliser plusieurs 2048-IMM-SD page 2).
    return pv_net_impos


@reference_formula
class ir_pv_immo(SimpleFormulaColumn):
    column = FloatCol(default = 0)
    entity_class = FoyersFiscaux
    label = u"Impôt sur le revenu afférent à la plus-value immobilière"
    url = "http://www.impots.gouv.fr/portal/dgi/public/popup?espId=1&typePage=cpr02&docOid=documentstandard_2157"

    def function(self, simulation, period):
        """
        Impôt sur le revenu afférent à la plus-value immobilière (CGI, art. 150 U, 150 UC-I et 150 UD)
        """
        period = period.start.offset('first-of', 'month').period('year')
        f3vz = simulation.calculate('f3vz', period)
        pv_immo = simulation.legislation_at(period.start).ir.pv_immo

        # 61. MONTANT DU PAR LES PERSONNES PHYSIQUES RESIDENTES DE FRANCE OU D’UN AUTRE ETAT MEMBRE DE L’EEE(1)
        # (VOIR TABLEAU PAGE 3).
        # if resident
        impo = pv_immo.taux*f3vz
    #    62. MONTANT DU PAR LES AUTRES NON-RESIDENTS (VOIR TABLEAU PAGE 3 ET REMPLIR PAGE 4 SI NECESSAIRE)
    #    IMPOSITION A 33,1/3% DES PERSONNES PHYSIQUES [(LIGNE 50 OU LIGNE 53) X 33,1/3%] = = €
    #    IMPOSITION A 15% OU 19% OU 33,1/3% DES PERSONNES MORALES NON ASSUJETTIES A L’IR, ETABLIES DANS UN ETAT
    #    MEMBRE DE L’EEE(1) (LIGNE 300 X 15% OU 19% OU 33,1/3%) = = €
    #IMPOSITION A 50% DES PERSONNES PHYSIQUES OU MORALES RESIDENTES D’UN ETNC(2)
    #[(LIGNE 50 OU (LIGNE 54 + LIGNE 300)) X 50%] = = €

    #63. ABATTEMENT REPRESENTATIF DU FORFAIT FORESTIER (SI LE CEDANT EST UNE PERSONNE PHYSIQUE RESIDENTE) - €
    #64. MONTANT DE L’IMPOT DU APRES ABATTEMENT [(LIGNE 61 + LIGNE 62) – LIGNE 63] = = €
    #(POUR L’APPLICATION DES PRELEVEMENTS SOCIAUX CI-DESSOUS, CF. TABLEAU « RAPPEL DES TAUX D’IMPOSITION » PAGE 5) :
        return period, -impo
