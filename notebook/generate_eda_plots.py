import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Style premium
sns.set_theme(style='whitegrid', palette='muted')
plt.rcParams['figure.dpi'] = 120
plt.rcParams['figure.figsize'] = (10, 5)

# 1. Charger les données
DATA_PATH = Path(__file__).parent / "../backend/data/processed/dataset_propre.csv"
df = pd.read_csv(
    DATA_PATH,
    parse_dates=['date_mutation'],
    dtype={'code_postal': str, 'code_insee': str, 'departement': str}
)
print(f"Données chargées : {len(df):,} transactions.")

# --- FIGURE 1: Distribution des prix ---
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Distribution prix total
axes[0].hist(df['prix'] / 1e6, bins=60, color='#378ADD', edgecolor='white', linewidth=0.4)
axes[0].set_title('Distribution des prix de vente')
axes[0].set_xlabel('Prix (millions €)')
axes[0].set_ylabel('Nombre de transactions')
median_prix = df['prix'].median() / 1e6
axes[0].axvline(median_prix, color='#D85A30', linestyle='--', linewidth=1.5, label=f'Médiane : {median_prix:.2f}M€')
axes[0].legend()

# Distribution prix au m²
axes[1].hist(df['prix_m2'], bins=60, color='#1D9E75', edgecolor='white', linewidth=0.4)
axes[1].set_title('Distribution du prix au m²')
axes[1].set_xlabel('Prix au m² (€)')
axes[1].set_ylabel('Nombre de transactions')
median_m2 = df['prix_m2'].median()
axes[1].axvline(median_m2, color='#D85A30', linestyle='--', linewidth=1.5, label=f'Médiane : {median_m2:,.0f} €/m²')
axes[1].legend()

plt.suptitle('Île-de-France - Distribution des prix', fontsize=13, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(Path(__file__).parent / '../docs/fig_distribution_prix.png', bbox_inches='tight', dpi=150)
plt.close()
print("Figure 1 (fig_distribution_prix.png) générée avec succès !")

# --- FIGURE 2: Analyse géographique (Départements et Top/Flop Codes Postaux) ---
prix_dept = (
    df.groupby('departement')['prix_m2']
    .median()
    .reset_index()
    .sort_values('prix_m2', ascending=False)
)

top_15 = (
    df.groupby('code_postal')['prix_m2']
    .median()
    .reset_index()
    .sort_values('prix_m2', ascending=False)
    .head(15)
)

bottom_15 = (
    df.groupby('code_postal')['prix_m2']
    .median()
    .reset_index()
    .sort_values('prix_m2', ascending=True)
    .head(15)
)

fig, axes = plt.subplots(3, 1, figsize=(14, 15))

# 1. Prix médian par département
axes[0].bar(prix_dept['departement'].astype(str), prix_dept['prix_m2'], color='#378ADD', edgecolor='white')
axes[0].set_title('Prix médian au m² par Département', fontsize=12, fontweight='bold')
axes[0].set_xlabel('Département')
axes[0].set_ylabel('Prix médian au m² (€)')
axes[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f} €'))

# 2. Top 15 des codes postaux les plus chers
axes[1].bar(top_15['code_postal'].astype(str), top_15['prix_m2'], color='#D85A30', edgecolor='white')
axes[1].set_title("Top 15 des codes postaux les plus chers d'Île-de-France", fontsize=12, fontweight='bold')
axes[1].set_xlabel('Code postal')
axes[1].set_ylabel('Prix médian au m² (€)')
axes[1].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f} €'))

# 3. Top 15 des codes postaux les moins chers (Flop 15)
axes[2].bar(bottom_15['code_postal'].astype(str), bottom_15['prix_m2'], color='#1D9E75', edgecolor='white')
axes[2].set_title("Top 15 des codes postaux les moins chers d'Île-de-France", fontsize=12, fontweight='bold')
axes[2].set_xlabel('Code postal')
axes[2].set_ylabel('Prix médian au m² (€)')
axes[2].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f} €'))

plt.suptitle('Analyse géographique des prix - Île-de-France', fontsize=14, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(Path(__file__).parent / '../docs/fig_prix_code_postal.png', bbox_inches='tight', dpi=150)
plt.close()
print("Figure 2 (fig_prix_code_postal.png) générée avec succès !")

# --- FIGURE 3: Corrélations features (Entière et Complète) ---
num_cols = ['prix', 'prix_m2', 'surface_m2', 'nb_pieces', 'score_dpe_median', 'score_georisques', 'score_delinquance', 'annee', 'latitude', 'longitude']
num_cols = [c for c in num_cols if c in df.columns]
corr = df[num_cols].corr()

fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(
    corr,
    annot=True,
    fmt='.2f',
    cmap='RdBu_r',
    center=0,
    ax=ax,
    square=True,
    linewidths=0.5,
    cbar_kws={'shrink': 0.8},
)
ax.set_title('Corrélations entre les features (Complète et Entière)', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(Path(__file__).parent / '../docs/fig_correlations.png', bbox_inches='tight', dpi=150)
plt.close()
print("Figure 3 (fig_correlations.png) générée avec succès !")

# --- FIGURES INTERACTIVES (PLOTLY) ---
import plotly.express as px

# 4. Carte interactive des prix au m²
sample = df.sample(min(5000, len(df)), random_state=42)
fig_map = px.scatter_mapbox(
    sample,
    lat='latitude',
    lon='longitude',
    color='prix_m2',
    size='surface_m2',
    color_continuous_scale='RdYlGn_r',
    range_color=[sample['prix_m2'].quantile(0.05), sample['prix_m2'].quantile(0.95)],
    hover_data={
        'prix': ':,.0f',
        'prix_m2': ':,.0f',
        'surface_m2': ':.0f',
        'type_bien': True,
        'nb_pieces': True,
    },
    mapbox_style='carto-positron',
    zoom=9,
    center={'lat': 48.8566, 'lon': 2.3522},
    title='Prix au m² — Île-de-France (75, 77, 78, 91, 92, 93, 94, 95)',
    labels={'prix_m2': 'Prix/m² (€)'},
    height=550,
)
fig_map.update_layout(margin=dict(l=0, r=0, t=40, b=0))
fig_map.write_html(Path(__file__).parent / '../docs/carte_prix_idf.html')
print("Figure 4 (carte_prix_idf.html) générée avec succès !")

# 5. Évolution du prix médian au m²
prix_temps = (
    df.groupby(['annee', 'type_bien'])['prix_m2']
    .median()
    .reset_index()
)
fig_evol = px.line(
    prix_temps,
    x='annee',
    y='prix_m2',
    color='type_bien',
    markers=True,
    title='Évolution du prix médian au m² — Île-de-France',
    labels={'prix_m2': 'Prix médian au m² (€)', 'annee': 'Année', 'type_bien': 'Type'},
    color_discrete_map={'Appartement': '#378ADD', 'Maison': '#D85A30'},
)
fig_evol.update_layout(yaxis_tickformat=',.0f')
fig_evol.write_html(Path(__file__).parent / '../docs/fig_evolution_prix.html')
print("Figure 5 (fig_evolution_prix.html) générée avec succès !")

# --- FIGURE 6: Risques et Délinquance par Département (Livrable Exact) ---
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# S'assurer que le département est trié et au format chaîne
df['departement_str'] = df['departement'].astype(str).str.zfill(2)

# Agréger le taux de délinquance par département (score constant par département)
del_agg = df.groupby('departement_str')['score_delinquance'].mean().reset_index().sort_values('score_delinquance', ascending=False)

# 1. Taux de délinquance par département (Barplot)
sns.barplot(
    x='departement_str',
    y='score_delinquance',
    data=del_agg,
    ax=axes[0],
    palette='Purples_r',
    hue='departement_str',
    legend=False,
    edgecolor='black',
    linewidth=0.5
)
axes[0].set_title('Taux de Délinquance Moyen par Département (Normalisé sur 10)', fontsize=12, fontweight='bold', pad=15)
axes[0].set_xlabel('Département')
axes[0].set_ylabel('Score Délinquance (sur 10)')
axes[0].set_ylim(0, 10)

# Ajouter les valeurs textuelles sur les barres
for p in axes[0].patches:
    height = p.get_height()
    axes[0].annotate(f'{height:.2f}',
                (p.get_x() + p.get_width() / 2., height + 0.1),
                ha='center', va='bottom', fontsize=10, fontweight='bold')

# 2. Distribution des risques environnementaux par département (Boxplot)
sns.boxplot(
    x='departement_str',
    y='score_georisques',
    data=df.sort_values('departement_str'),
    ax=axes[1],
    palette='YlOrRd',
    hue='departement_str',
    legend=False,
    linewidth=1.2,
    fliersize=3
)
axes[1].set_title('Distribution des scores Géorisques par Département', fontsize=12, fontweight='bold', pad=15)
axes[1].set_xlabel('Département')
axes[1].set_ylabel('Score Géorisques (sur 10)')
axes[1].set_ylim(-0.5, 10.5)

plt.suptitle('Analyse comparative de la Délinquance et des Risques environnementaux par Département en Île-de-France', fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout()

# Sauvegarde
plt.savefig(Path(__file__).parent / '../docs/fig_risques_delinquance_departement.png', bbox_inches='tight', dpi=150)
plt.close()
print("Figure 6 (fig_risques_delinquance_departement.png) générée avec succès !")


