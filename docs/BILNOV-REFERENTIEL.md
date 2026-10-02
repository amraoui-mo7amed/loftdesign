# Store Bilnov : référentiel produit de l'écosystème Bilnov

Store Bilnov est la source de vérité des produits pour Bilnov Project, le viewer BIM/IFC,
Bilnov 360 et les futurs plugins SketchUp / Revit / Archicad.

## Identifiants

| Identifiant | Champ | Rôle |
|---|---|---|
| BPID | `Product.bpid` (ex. `BPID-000002548`) | BILNOV Product ID. Attribué à la création, ne change jamais (nom, prix, fournisseur, images, fichiers, catégorie). Jamais dérivé du nom. |
| Variant ID | `ProductItem.variant_id` (ex. `BPID-000002548-V02`) | Une variante (couleur, finition, dimension). Le rang n'est jamais réutilisé. |
| SKU | `ProductItem.sku` / `Product.sku` | Référence commerciale du vendeur. Unique dans le catalogue. |
| Manufacturer ID | `Manufacturer.manufacturer_id` (ex. `MFR-00012`) | Le fabricant (différent de la marque et du fournisseur). |
| Manufacturer Reference | `Product.manufacturer_reference`, `ProductItem.manufacturer_reference` | Référence catalogue du fabricant. |
| Supplier ID | `Product.supplier_id` (ex. `SUP-00007`) | Le compte fournisseur qui vend sur le Store. |
| UUID | `Product.bilnov_uuid` | Identifiant interne immuable. |
| IFC GUID | jamais stocké sur le produit | Une instance placée dans un projet BILNOV. |

## Fichiers de conception

`ProductAsset` : SKP, RFA, GSM, IFC, GLB/GLTF, OBJ, FBX, DWG, textures, PDF, éventuellement par variante.
Un nouvel envoi du même format crée la version suivante ; les anciennes restent téléchargeables
et `Product.model_version` augmente. Un projet garde la version qu'il utilise : le store ne remplace rien.

## Métadonnées dans les fichiers

`Pset_BilnovProduct` (IFC), attributs de composant (SketchUp, dictionnaire `BilnovProduct`) et
`extras.bilnov` (GLB/GLTF) portent les mêmes clés : BilnovProductID, BilnovVariantID, Manufacturer,
ManufacturerReference, StoreURL, ModelVersion (+ ProductName, SKU, CategoryCode).
Renvoyé prêt à écrire par `GET /api/catalog/products/{bpid}/`.

## API catalogue (lecture seule, publique)

```
GET  /api/catalog/products/{bpid}/                fiche + variantes + fichiers + Pset
GET  /api/catalog/products/{bpid}/variants/
GET  /api/catalog/products/{bpid}/assets/[?all=1] fichiers (versions courantes ou toutes)
GET  /api/catalog/products/{bpid}/availability/
GET  /api/catalog/products/{bpid}/prices/         prix public DZD / EUR
GET  /api/catalog/products/{bpid}/suppliers/
GET  /api/catalog/products/{bpid}/alternatives/   même catégorie, prix ±50 %
GET  /api/catalog/search/?q=&category=&format=&limit=
POST /api/catalog/bim/resolve/                    {"objects":[{"bpid","variantId","ifcGuid","sku"}]}
GET  /store/product/{bpid}/                       lien permanent (StoreURL des fichiers)
```

`bim/resolve` classe chaque objet : `identified`, `unavailable` (n'est plus en stock),
`unknown` (BPID inconnu) ou `generic` (sans BPID, à rapprocher d'un produit du store).
Prix d'achat fournisseur et commissions ne sortent jamais par l'API.

## Ce qui revient à Bilnov Project (hors de ce dépôt)

Table `ProjectObject` (project_id, bpid, variant_id, sku, manufacturer_id, ifc_guid,
source_software, source_object_id, model_version, quantity, unit, room/level/model, status),
nomenclature (BOQ), liste d'achat du projet, prescriptions, hotspots 360, plugins CAO, matching IA.
Ces briques appellent l'API ci-dessus et ne stockent que le BPID, jamais une copie de la fiche.
