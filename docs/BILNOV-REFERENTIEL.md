# Store Bilnov : référentiel produit de l'écosystème Bilnov

Store Bilnov est la source de vérité des produits pour Bilnov Project, le viewer BIM/IFC,
Bilnov 360 et les futurs plugins SketchUp / Revit / Archicad.

## Identifiants

| Identifiant | Champ | Rôle |
|---|---|---|
| BOID | `Product.bilnov_object_id` (ex. `BLV-FUR-0000000125`) | Le produit du catalogue. Attribué à la création, ne change jamais (prix, fournisseur, images, fichiers, catégorie). |
| UUID | `Product.bilnov_uuid` | Identifiant interne immuable (`boid:<uuid>`). |
| SKU | `ProductItem.sku` (ex. `SKU-LUNA-BLK`) | Une variante commerciale. Unique dans tout le catalogue. |
| IFC GUID | jamais stocké sur le produit | Une instance placée dans un projet. Appartient à Bilnov Project (`ProjectObject.ifc_guid`). |

Le code à 3 lettres vient de la catégorie (`Category.code` : FUR, LGT, TIL...), `GEN` sinon.

## Fichiers de conception

`ProductAsset` : SKP, RFA, GSM, IFC, GLB/GLTF, OBJ, FBX, DWG, textures, PDF, éventuellement par variante.
Un nouvel envoi du même format crée la version suivante ; les anciennes restent téléchargeables
et `Product.model_version` augmente. Un projet garde la version qu'il utilise : le store ne remplace rien.

## Property set IFC

`Pset_BilnovProduct` : BilnovObjectID, BilnovSKU, BilnovProductName, BilnovManufacturerID,
BilnovManufacturerName, BilnovCategoryID, BilnovCollectionID, BilnovStoreURL,
BilnovProductVersion, BilnovVariantID. Renvoyé prêt à écrire par `GET /api/catalog/products/{boid}/`.

## API catalogue (lecture seule, publique)

```
GET  /api/catalog/products/{boid}/                fiche + variantes + fichiers + Pset
GET  /api/catalog/products/{boid}/variants/
GET  /api/catalog/products/{boid}/assets/[?all=1] fichiers (versions courantes ou toutes)
GET  /api/catalog/products/{boid}/availability/
GET  /api/catalog/products/{boid}/prices/         prix public DZD / EUR
GET  /api/catalog/products/{boid}/suppliers/
GET  /api/catalog/products/{boid}/alternatives/   même catégorie, prix ±50 %
GET  /api/catalog/search/?q=&category=&format=&limit=
POST /api/catalog/bim/resolve/                    {"objects":[{"bilnovObjectId","ifcGuid","sku"}]}
GET  /store/product/{boid}/                       lien permanent (StoreURL des fichiers)
```

`bim/resolve` classe chaque objet : `identified`, `unavailable` (n'est plus en stock),
`unknown` (BOID inconnu) ou `generic` (sans BOID, à rapprocher d'un produit du store).
Prix d'achat fournisseur et commissions ne sortent jamais par l'API.

## Ce qui revient à Bilnov Project (hors de ce dépôt)

Table `ProjectObject` (project_id, bilnov_object_id, variant_id, sku, manufacturer_id, ifc_guid,
source_software, source_object_id, model_version, quantity, unit, room/level/model, status),
nomenclature (BOQ), liste d'achat du projet, prescriptions, hotspots 360, plugins CAO, matching IA.
Ces briques appellent l'API ci-dessus et ne stockent que le BOID, jamais une copie de la fiche.
