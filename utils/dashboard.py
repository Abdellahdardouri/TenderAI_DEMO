import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import calendar
from datetime import datetime
import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def load_data_from_supabase():
    """
    Load data from Supabase database
    """
    try:
        # Get Supabase credentials
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            raise Exception("SUPABASE_URL et SUPABASE_KEY doivent être configurés dans le fichier .env")
        
        # Create Supabase client
        supabase = create_client(url, key)
        
        # Fetch all data from tender_ai table
        response = supabase.table("tender_ai").select("*").execute()
        
        if response.data:
            # Convert to DataFrame
            df = pd.DataFrame(response.data)
            
            # Process the data similar to the Excel version
            df = prepare_data(df)
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        raise Exception(f"Erreur lors du chargement des données Supabase: {str(e)}")

def prepare_data(df):
    """
    Prepare and clean data from Supabase - mapping column names to match Excel structure
    """
    if df.empty:
        return df
    
    try:
        # Map Supabase columns to expected column names
        # Based on your Supabase table structure vs Excel structure
        column_mapping = {
            'reference_ao': 'Référence AO',
            'organisme_emetteur': 'Organisme émetteur', 
            'region_ville': 'Région / Ville',
            'montant_estime_mad': 'Montant estimé (MAD)',
            'caution_demandee_mad': 'Caution demandée (MAD)',
            'secteur': 'Secteur',
            'date_de_publication': 'Date de publication',
            'go_no_go': 'GO / NO GO',
            'date_de_soumission': 'Date de soumission',
            'statut': 'Statut',
            'montant_offert_mad': 'Montant offert (MAD)',
            'motif_de_rejet': 'Motif de rejet',
            'objet_de_l_appel_d_offre': 'Objet de l\'appel d\'offre',
            'date_de_decision': 'Date de décision',
            'identifiant_unique': 'Identifiant unique',
            'temps_de_traitement_jours': 'Temps de traitement (jours)',
            'ecart_montant': 'Écart montant (%)',
            'duree_du_marche_mois': 'Durée du marché (mois)',
            'complexite_percue_1_5': 'Complexité perçue (1-5)',
            'score_technique_si_dispo': 'Score technique (si dispo)',
            'nombre_de_concurrents_si_dispo': 'Nombre de concurrents (si dispo)',
            'responsable': 'Responsable',
            'type_de_mission': 'Type de mission',
            'historique_avec_mo': 'Historique avec MO',
            'lien_vers_dossier': 'Lien vers dossier'
        }
        
        # Rename columns if they exist
        df = df.rename(columns=column_mapping)
        
        # Convert date columns to datetime
        date_columns = ['Date de publication', 'Date de soumission', 'Date de décision']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Helper function to safely convert to numeric
        def safe_numeric_conversion(series):
            try:
                return pd.to_numeric(series, errors='coerce')
            except:
                return series
        
        # Convert numeric columns to proper numeric types
        numeric_columns = [
            'Montant estimé (MAD)', 'Caution demandée (MAD)', 'Montant offert (MAD)',
            'Temps de traitement (jours)', 'Écart montant (%)', 'Durée du marché (mois)',
            'Complexité perçue (1-5)', 'Score technique (si dispo)', 'Nombre de concurrents (si dispo)'
        ]
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = safe_numeric_conversion(df[col])
                
        # Calculate additional fields if they don't exist
        if all(col in df.columns for col in ['Date de publication', 'Date de soumission']):
            if 'Temps de traitement (jours)' not in df.columns or df['Temps de traitement (jours)'].isna().all():
                df['Temps de traitement (jours)'] = (df['Date de soumission'] - df['Date de publication']).dt.days
            
        # Calculate price difference percentage
        price_cols = ['Montant estimé (MAD)', 'Montant offert (MAD)']
        if all(col in df.columns for col in price_cols):
            if 'Écart montant (%)' not in df.columns or df['Écart montant (%)'].isna().all():
                # Ensure both columns are numeric before calculation
                montant_estime = safe_numeric_conversion(df['Montant estimé (MAD)'])
                montant_offert = safe_numeric_conversion(df['Montant offert (MAD)'])
                
                # Calculate percentage difference, handling division by zero
                with np.errstate(divide='ignore', invalid='ignore'):
                    df['Écart montant (%)'] = np.where(
                        montant_estime != 0,
                        ((montant_offert - montant_estime) / montant_estime * 100).round(2),
                        0
                    )
            
        # Create month and year columns
        if 'Date de publication' in df.columns:
            df['Mois'] = df['Date de publication'].dt.month
            df['Mois_Nom'] = df['Date de publication'].dt.month.apply(
                lambda x: calendar.month_name[x] if pd.notna(x) and isinstance(x, (int, float)) else "Inconnu")
            df['Année'] = df['Date de publication'].dt.year
            
        # Add strategic score
        required_cols = ['Montant estimé (MAD)', 'Statut', 'Complexité perçue (1-5)']
        if all(col in df.columns for col in required_cols):
            df['Gagné_bool'] = df['Statut'].apply(lambda x: 1 if str(x).lower() == 'gagné' else 0)
            
            # Safely calculate strategic score
            montant_estime = safe_numeric_conversion(df['Montant estimé (MAD)'])
            complexite = safe_numeric_conversion(df['Complexité perçue (1-5)'])
            
            df['Score AO stratégique'] = np.where(
                (pd.notna(montant_estime)) & (pd.notna(complexite)) & (complexite > 0),
                (montant_estime * df['Gagné_bool']) / complexite,
                0
            )
        
        # Handle alternative column names that might exist in Supabase
        # Map common variations
        if 'Région' not in df.columns and 'Région / Ville' in df.columns:
            df['Région'] = df['Région / Ville']
        
        if 'Caution (MAD)' not in df.columns and 'Caution demandée (MAD)' in df.columns:
            df['Caution (MAD)'] = df['Caution demandée (MAD)']
            
        if 'Décision GO/NO GO' not in df.columns and 'GO / NO GO' in df.columns:
            df['Décision GO/NO GO'] = df['GO / NO GO']
            
        return df
    except Exception as e:
        raise Exception(f"Erreur lors de la préparation des données: {str(e)}")

def calculate_kpis(df):
    """
    Calculate KPIs for dashboard
    """
    kpis = {
        'total_ao': len(df),
        'go_rate': 0,
        'response_rate': 0,
        'success_rate': 0,
        'avg_estimated': 0,
        'avg_offered': 0,
        'avg_price_diff': 0,
        'avg_deposit': 0,
        'avg_complexity': 0
    }
    
    if df.empty:
        return kpis
    
    try:
        # Calculate GO/NO GO rate
        go_col = None
        for col in ['Décision GO/NO GO', 'GO / NO GO']:
            if col in df.columns:
                go_col = col
                break
        
        if go_col:
            kpis['go_rate'] = (df[go_col] == 'GO').mean() * 100
        
        # Calculate response rate
        if 'Statut' in df.columns:
            kpis['response_rate'] = (~df['Statut'].isna()).mean() * 100
        
        # Calculate success rate
        if 'Statut' in df.columns:
            kpis['success_rate'] = (df['Statut'] == 'Gagné').mean() * 100
        
        # Helper function to safely calculate numeric means
        def safe_numeric_mean(series):
            try:
                # Convert to numeric, coercing errors to NaN
                numeric_series = pd.to_numeric(series, errors='coerce')
                return numeric_series.mean() if not numeric_series.isna().all() else 0
            except:
                return 0
        
        # Calculate average estimated amount
        if 'Montant estimé (MAD)' in df.columns:
            kpis['avg_estimated'] = safe_numeric_mean(df['Montant estimé (MAD)'])
        
        # Calculate average offered amount
        if 'Montant offert (MAD)' in df.columns:
            kpis['avg_offered'] = safe_numeric_mean(df['Montant offert (MAD)'])
        
        # Calculate average price difference
        if 'Écart montant (%)' in df.columns:
            kpis['avg_price_diff'] = safe_numeric_mean(df['Écart montant (%)'])
        
        # Calculate average deposit
        deposit_col = None
        for col in ['Caution (MAD)', 'Caution demandée (MAD)']:
            if col in df.columns:
                deposit_col = col
                break
        
        if deposit_col:
            kpis['avg_deposit'] = safe_numeric_mean(df[deposit_col])
        
        # Calculate average complexity
        if 'Complexité perçue (1-5)' in df.columns:
            kpis['avg_complexity'] = safe_numeric_mean(df['Complexité perçue (1-5)'])
            
    except Exception as e:
        print(f"Error in calculate_kpis: {str(e)}")
        # Return default values if there's an error
        pass
    
    return kpis

def create_monthly_tenders_chart(df):
    """
    Create histogram of monthly tenders
    """
    if df.empty or 'Mois_Nom' not in df.columns or 'Année' not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="Données insuffisantes pour afficher ce graphique", 
                          xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                          font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig
    
    try:
        # Count tenders by month-year
        monthly_counts = df.groupby(['Année', 'Mois', 'Mois_Nom']).size().reset_index(name='Nombre d\'AO')
        
        # Create a proper sort order
        month_order = {name: i for i, name in enumerate(calendar.month_name) if name}
        monthly_counts['Mois_tri'] = monthly_counts['Mois_Nom'].map(month_order)
        monthly_counts = monthly_counts.sort_values(['Année', 'Mois_tri'])
        
        # Create month-year labels
        monthly_counts['Période'] = monthly_counts['Mois_Nom'] + ' ' + monthly_counts['Année'].astype(str)
        
        # Create bar chart
        fig = px.bar(monthly_counts, x='Période', y='Nombre d\'AO', 
                    title="Nombre d'appels d'offres par mois",
                    text_auto=True,
                    color_discrete_sequence=['#36A2EB'])
        
        # Update layout
        fig.update_layout(
            xaxis_title="Mois", 
            yaxis_title="Nombre d'AO",
            plot_bgcolor='rgba(0,0,0,0.05)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        # Add grid lines
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.2)')
        
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Erreur lors de la création du graphique: {str(e)}", 
                         xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                         font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig

def create_sector_pie_chart(df):
    """
    Create pie chart of sectors
    """
    if 'Secteur' not in df.columns or df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Données insuffisantes pour afficher ce graphique", 
                          xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                          font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig
    
    try:
        # Count tenders by sector
        sector_counts = df['Secteur'].value_counts().reset_index()
        sector_counts.columns = ['Secteur', 'Nombre d\'AO']
        
        # Create pie chart
        fig = px.pie(sector_counts, names='Secteur', values='Nombre d\'AO', 
                    title="Répartition des appels d'offres par secteur",
                    color_discrete_sequence=px.colors.qualitative.Set3)
        
        # Update layout
        fig.update_layout(
            legend_title="Secteur",
            plot_bgcolor='rgba(0,0,0,0.05)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Erreur lors de la création du graphique: {str(e)}", 
                         xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                         font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig

def create_region_map(df):
    """
    Create map of tenders by region
    """
    region_col = None
    for col in ['Région', 'Région / Ville']:
        if col in df.columns:
            region_col = col
            break
    
    if not region_col or df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Données insuffisantes pour afficher ce graphique", 
                          xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                          font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig
    
    try:
        # Count tenders by region
        region_counts = df[region_col].value_counts().reset_index()
        region_counts.columns = ['Région', 'Nombre d\'AO']
        
        # Create bar chart instead of map for simplicity
        fig = px.bar(region_counts, x='Région', y='Nombre d\'AO', 
                    title="Répartition géographique des appels d'offres",
                    color_discrete_sequence=['#FF6B6B'])
        
        # Update layout
        fig.update_layout(
            xaxis_title="Région/Ville", 
            yaxis_title="Nombre d'AO",
            plot_bgcolor='rgba(0,0,0,0.05)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        # Add grid lines
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.2)')
        
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Erreur lors de la création du graphique: {str(e)}", 
                         xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                         font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig

def create_amount_by_organization(df):
    """
    Create bar chart of amounts by organization
    """
    if 'Organisme émetteur' not in df.columns or 'Montant estimé (MAD)' not in df.columns or df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Données insuffisantes pour afficher ce graphique", 
                          xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                          font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig
    
    try:
        # Sum amounts by organization
        amount_by_org = df.groupby('Organisme émetteur')['Montant estimé (MAD)'].sum().reset_index()
        amount_by_org = amount_by_org.sort_values('Montant estimé (MAD)', ascending=False).head(10)
        
        # Convert to millions for better readability
        amount_by_org['Montant (Millions MAD)'] = amount_by_org['Montant estimé (MAD)'] / 1000000
        
        # Create bar chart
        fig = px.bar(amount_by_org, x='Organisme émetteur', y='Montant (Millions MAD)', 
                    title="Montant total des AO par organisme (Millions MAD)",
                    text_auto='.2f',
                    color_discrete_sequence=['#FF6384'])
        
        # Update layout
        fig.update_layout(
            xaxis_title="Organisme émetteur", 
            yaxis_title="Montant total (Millions MAD)",
            plot_bgcolor='rgba(0,0,0,0.05)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        # Add grid lines
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.2)')
        
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Erreur lors de la création du graphique: {str(e)}", 
                         xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                         font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig

def create_deposit_by_organization(df):
    """
    Create bar chart of deposits by organization
    """
    deposit_col = None
    for col in ['Caution (MAD)', 'Caution demandée (MAD)']:
        if col in df.columns:
            deposit_col = col
            break
    
    if 'Organisme émetteur' not in df.columns or not deposit_col or df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Données insuffisantes pour afficher ce graphique", 
                          xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                          font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig
    
    try:
        # Average deposit by organization
        deposit_by_org = df.groupby('Organisme émetteur')[deposit_col].mean().reset_index()
        deposit_by_org = deposit_by_org.sort_values(deposit_col, ascending=False).head(10)
        
        # Create bar chart
        fig = px.bar(deposit_by_org, x='Organisme émetteur', y=deposit_col, 
                    title="Caution moyenne par organisme (MAD)",
                    text_auto='.2f',
                    color_discrete_sequence=['#FFCE56'])
        
        # Update layout
        fig.update_layout(
            xaxis_title="Organisme émetteur", 
            yaxis_title="Caution moyenne (MAD)",
            plot_bgcolor='rgba(0,0,0,0.05)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        # Add grid lines
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.2)')
        
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Erreur lors de la création du graphique: {str(e)}", 
                         xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                         font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig

def create_duration_by_sector(df):
    """
    Create histogram of contract duration by sector
    """
    if 'Secteur' not in df.columns or 'Durée du marché (mois)' not in df.columns or df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Données insuffisantes pour afficher ce graphique", 
                          xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                          font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig
    
    try:
        # Average duration by sector
        duration_by_sector = df.groupby('Secteur')['Durée du marché (mois)'].mean().reset_index()
        duration_by_sector = duration_by_sector.sort_values('Durée du marché (mois)', ascending=False)
        
        # Create bar chart
        fig = px.bar(duration_by_sector, x='Secteur', y='Durée du marché (mois)', 
                    title="Durée moyenne des marchés par secteur (mois)",
                    text_auto='.1f',
                    color_discrete_sequence=['#4BC0C0'])
        
        # Update layout
        fig.update_layout(
            xaxis_title="Secteur", 
            yaxis_title="Durée moyenne (mois)",
            plot_bgcolor='rgba(0,0,0,0.05)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        # Add grid lines
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.2)')
        
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Erreur lors de la création du graphique: {str(e)}", 
                         xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                         font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig

def create_top_organizations_chart(df):
    """
    Create bar chart of top organizations by amount
    """
    if 'Organisme émetteur' not in df.columns or 'Montant estimé (MAD)' not in df.columns or df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Données insuffisantes pour afficher ce graphique", 
                          xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                          font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig
    
    try:
        # Sum amounts by organization and get top 5
        top_orgs = df.groupby('Organisme émetteur')['Montant estimé (MAD)'].sum().nlargest(5).reset_index()
        
        # Format amounts (in millions)
        top_orgs['Montant (Millions MAD)'] = top_orgs['Montant estimé (MAD)'] / 1000000
        
        # Create bar chart
        fig = px.bar(top_orgs, x='Organisme émetteur', y='Montant (Millions MAD)', 
                    title="Top 5 des maîtres d'ouvrage par montant total (Millions MAD)",
                    text_auto='.2f',
                    color_discrete_sequence=['#9966FF'])
        
        # Update layout
        fig.update_layout(
            xaxis_title="Maître d'ouvrage", 
            yaxis_title="Montant total (Millions MAD)",
            plot_bgcolor='rgba(0,0,0,0.05)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        # Add grid lines
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.2)')
        
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Erreur lors de la création du graphique: {str(e)}", 
                         xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                         font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig

def create_latest_tenders_table(df):
    """
    Create table of 5 latest tenders
    """
    if 'Date de publication' not in df.columns or df.empty:
        return pd.DataFrame({'Message': ['Données insuffisantes pour afficher le tableau']})
    
    try:
        # Sort by publication date (descending) and get latest 5
        latest_tenders = df.sort_values('Date de publication', ascending=False).head(5)
        
        # Select relevant columns
        cols_to_show = ['Référence AO', 'Organisme émetteur', 'Secteur', 'Date de publication', 
                       'Montant estimé (MAD)', 'Statut']
        
        # Keep only columns that exist in the dataframe
        cols_to_show = [col for col in cols_to_show if col in latest_tenders.columns]
        
        if not cols_to_show:
            return pd.DataFrame({'Message': ['Données insuffisantes pour afficher le tableau']})
            
        latest_tenders = latest_tenders[cols_to_show].copy()
        
        # Format date column
        if 'Date de publication' in latest_tenders.columns:
            latest_tenders['Date de publication'] = latest_tenders['Date de publication'].dt.strftime('%d/%m/%Y')
        
        # Format monetary values
        if 'Montant estimé (MAD)' in latest_tenders.columns:
            latest_tenders['Montant estimé (MAD)'] = latest_tenders['Montant estimé (MAD)'].apply(
                lambda x: f"{x:,.2f} MAD" if pd.notna(x) else "N/A")
        
        return latest_tenders
    except Exception as e:
        return pd.DataFrame({'Message': [f'Erreur: {str(e)}']})

def create_top_strategic_tenders(df):
    """
    Create table of top 5 tenders by strategic score
    """
    if 'Score AO stratégique' not in df.columns or df.empty:
        return pd.DataFrame({'Message': ['Données insuffisantes pour afficher le tableau']})
    
    try:
        # Sort by strategic score (descending) and get top 5
        top_strategic = df.sort_values('Score AO stratégique', ascending=False).head(5)
        
        # Select relevant columns
        cols_to_show = ['Référence AO', 'Organisme émetteur', 'Secteur', 'Montant estimé (MAD)', 
                       'Complexité perçue (1-5)', 'Statut', 'Score AO stratégique']
        
        # Keep only columns that exist in the dataframe
        cols_to_show = [col for col in cols_to_show if col in top_strategic.columns]
        
        if not cols_to_show:
            return pd.DataFrame({'Message': ['Données insuffisantes pour afficher le tableau']})
            
        top_strategic = top_strategic[cols_to_show].copy()
        
        # Format monetary values
        if 'Montant estimé (MAD)' in top_strategic.columns:
            top_strategic['Montant estimé (MAD)'] = top_strategic['Montant estimé (MAD)'].apply(
                lambda x: f"{x:,.2f} MAD" if pd.notna(x) else "N/A")
        
        return top_strategic
    except Exception as e:
        return pd.DataFrame({'Message': [f'Erreur: {str(e)}']})

def create_rejection_reasons_chart(df):
    """
    Create bar chart of rejection reasons
    """
    if 'Motif de rejet' not in df.columns or df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Données insuffisantes pour afficher ce graphique", 
                          xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                          font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig
    
    try:
        # Count rejection reasons
        rejection_counts = df['Motif de rejet'].value_counts().reset_index()
        rejection_counts.columns = ['Motif de rejet', 'Nombre']
        
        # Remove rows with NaN or empty rejection reasons
        rejection_counts = rejection_counts[~(rejection_counts['Motif de rejet'].isna() | 
                                            (rejection_counts['Motif de rejet'] == ''))]
        
        if rejection_counts.empty:
            fig = go.Figure()
            fig.add_annotation(text="Pas de motifs de rejet trouvés dans les données", 
                          xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                          font=dict(color='white'))
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
            return fig
        
        # Create bar chart
        fig = px.bar(rejection_counts, x='Motif de rejet', y='Nombre', 
                    title="Causes de rejet",
                    text_auto=True,
                    color_discrete_sequence=['#FF9F40'])
        
        # Update layout
        fig.update_layout(
            xaxis_title="Motif de rejet", 
            yaxis_title="Nombre d'occurrences",
            plot_bgcolor='rgba(0,0,0,0.05)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        # Add grid lines
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.2)')
        
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Erreur lors de la création du graphique: {str(e)}", 
                         xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                         font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig

def create_processing_by_consultant(df):
    """
    Create bar chart of processing scores by consultant
    """
    if 'Temps de traitement (jours)' not in df.columns or df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Données insuffisantes pour afficher ce graphique", 
                          xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                          font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig
    
    try:
        # Check if Responsable column exists
        if 'Responsable' not in df.columns:
            # Create a dummy responsable column for visualization
            consultants = ['Ahmed', 'Rachid', 'Fatima', 'Karima', 'Karim']
            df = df.copy()
            df['Responsable'] = np.random.choice(consultants, size=len(df))
        
        # Average processing time by consultant
        df_with_time = df.dropna(subset=['Temps de traitement (jours)'])
        if df_with_time.empty:
            fig = go.Figure()
            fig.add_annotation(text="Données insuffisantes pour afficher ce graphique", 
                              xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                              font=dict(color='white'))
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
            return fig
            
        consultant_processing = df_with_time.groupby('Responsable')['Temps de traitement (jours)'].mean().reset_index()
        consultant_processing = consultant_processing.sort_values('Temps de traitement (jours)')
        
        # Create bar chart
        fig = px.bar(consultant_processing, x='Responsable', y='Temps de traitement (jours)', 
                    title="Temps de traitement moyen par consultant (jours)",
                    text_auto='.1f',
                    color_discrete_sequence=['#9966FF'])
        
        # Update layout
        fig.update_layout(
            xaxis_title="Consultant", 
            yaxis_title="Temps moyen (jours)",
            plot_bgcolor='rgba(0,0,0,0.05)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        # Add grid lines
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.2)')
        
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Erreur lors de la création du graphique: {str(e)}", 
                         xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                         font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig

def create_complexity_vs_success_heatmap(df):
    """
    Create heatmap of complexity vs success
    """
    if 'Statut' not in df.columns or df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Données insuffisantes pour afficher ce graphique", 
                          xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                          font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig
    
    try:
        # Check if complexity column exists
        if 'Complexité perçue (1-5)' not in df.columns:
            # Create a dummy complexity column for visualization
            df = df.copy()
            df['Complexité perçue (1-5)'] = np.random.randint(1, 6, size=len(df))
            
        # Create a crosstab of complexity vs status
        complexity_status = pd.crosstab(df['Complexité perçue (1-5)'], df['Statut'], normalize='index') * 100
        
        # If 'Gagné' is not in the columns, add it with zeros
        if 'Gagné' not in complexity_status.columns:
            complexity_status['Gagné'] = 0
        
        # Create heatmap
        fig = px.imshow(complexity_status,
                       labels=dict(x="Statut", y="Complexité perçue (1-5)", color="Pourcentage (%)"),
                       x=complexity_status.columns,
                       y=complexity_status.index,
                       color_continuous_scale="RdBu_r",
                       title="Relation entre complexité et réussite (%)")
        
        # Add text annotations
        for i in range(len(complexity_status.index)):
            for j in range(len(complexity_status.columns)):
                fig.add_annotation(
                    x=j,
                    y=i,
                    text=f"{complexity_status.iloc[i, j]:.1f}%",
                    showarrow=False,
                    font=dict(color="white" if abs(complexity_status.iloc[i, j] - 50) > 30 else "black")
                )
        
        # Update layout
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0.05)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Erreur lors de la création du graphique: {str(e)}", 
                         xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                         font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig

def create_success_rate_evolution(df):
    """
    Create line chart of success rate evolution over time
    """
    if 'Statut' not in df.columns or 'Date de publication' not in df.columns or df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Données insuffisantes pour afficher ce graphique", 
                          xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                          font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig
    
    try:
        # Create a copy to avoid modifying original dataframe
        df_copy = df.copy()
        
        # Create year-month field
        df_copy['Année-Mois'] = df_copy['Date de publication'].dt.strftime('%Y-%m')
        
        # Calculate success rate by month
        monthly_success = df_copy.groupby('Année-Mois')['Statut'].apply(
            lambda x: (x == 'Gagné').sum() / len(x) * 100 if len(x) > 0 else 0
        ).reset_index()
        monthly_success.columns = ['Année-Mois', 'Taux de succès (%)']
        
        # Sort by year-month
        monthly_success = monthly_success.sort_values('Année-Mois')
        
        # Create line chart
        fig = px.line(monthly_success, x='Année-Mois', y='Taux de succès (%)', 
                     title="Évolution du taux de succès mensuel",
                     markers=True,
                     color_discrete_sequence=['#4BC0C0'])
        
        # Update layout
        fig.update_layout(
            xaxis_title="Mois", 
            yaxis_title="Taux de succès (%)",
            plot_bgcolor='rgba(0,0,0,0.05)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        # Add grid lines
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.2)')
        
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Erreur lors de la création du graphique: {str(e)}", 
                         xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                         font=dict(color='white'))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0.05)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
        return fig

def format_currency(value):
    """Format a number as currency (MAD)"""
    if pd.isna(value):
        return "N/A"
    return f"{value:,.2f} MAD"

def format_percentage(value):
    """Format a number as percentage"""
    if pd.isna(value):
        return "N/A"
    return f"{value:.2f}%"

# Additional utility functions for data processing
def create_sample_data():
    """
    Create sample data for testing (not used in production)
    This function is kept for development purposes only
    """
    import numpy as np
    
    # Create a dataframe with sample data
    np.random.seed(42)
    num_rows = 100
    
    # Create date range
    start_date = pd.Timestamp('2023-01-01')
    end_date = pd.Timestamp('2023-12-31')
    date_range = pd.date_range(start=start_date, end=end_date, periods=num_rows)
    
    # Create sectors
    sectors = ['BTP', 'IT', 'Énergie', 'Transport', 'Santé', 'Éducation', 'Agriculture']
    
    # Create regions
    regions = ['Casablanca-Settat', 'Rabat-Salé-Kénitra', 'Fès-Meknès', 'Marrakech-Safi', 
              'Tanger-Tétouan-Al Hoceima', 'Souss-Massa', 'Oriental']
    
    # Create organizations
    organizations = ['Ministère X', 'Office Y', 'Commune Z', 'Agence W', 'Direction V', 
                    'Établissement U', 'Société T']
    
    # Create statuses
    statuses = ['En cours', 'Gagné', 'Perdu', 'Abandonné', 'Rejeté']
    
    # Create rejection reasons
    rejection_reasons = ['Prix trop élevé', 'Dossier incomplet', 'Hors délai', 
                        'Non conforme au CPS', 'Concurrent moins-disant']
    
    # Create responsibles
    responsibles = ['Ahmed', 'Rachid', 'Fatima', 'Karima', 'Karim']
    
    # Generate random data
    data = {
        'Référence AO': [f'AO-{i:03d}-{np.random.randint(2020, 2024)}' for i in range(num_rows)],
        'Date de publication': date_range,
        'Date de soumission': [date + pd.Timedelta(days=np.random.randint(7, 60)) for date in date_range],
        'Organisme émetteur': np.random.choice(organizations, size=num_rows),
        'Secteur': np.random.choice(sectors, size=num_rows),
        'Région / Ville': np.random.choice(regions, size=num_rows),
        'Montant estimé (MAD)': np.random.uniform(100000, 10000000, size=num_rows),
        'Montant offert (MAD)': np.random.uniform(100000, 10000000, size=num_rows),
        'Caution demandée (MAD)': np.random.uniform(1000, 100000, size=num_rows),
        'Durée du marché (mois)': np.random.randint(3, 36, size=num_rows),
        'Complexité perçue (1-5)': np.random.randint(1, 6, size=num_rows),
        'GO / NO GO': np.random.choice(['GO', 'NO GO'], size=num_rows, p=[0.8, 0.2]),
        'Statut': np.random.choice(statuses, size=num_rows, p=[0.15, 0.35, 0.25, 0.15, 0.1]),
        'Motif de rejet': np.random.choice(rejection_reasons + [None], size=num_rows, p=[0.05, 0.05, 0.05, 0.05, 0.05, 0.75]),
        'Responsable': np.random.choice(responsibles, size=num_rows),
    }
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Create additional fields
    df['Temps de traitement (jours)'] = (df['Date de soumission'] - df['Date de publication']).dt.days
    df['Écart montant (%)'] = ((df['Montant offert (MAD)'] - df['Montant estimé (MAD)']) / 
                            df['Montant estimé (MAD)'] * 100).round(2)
    df['Mois'] = df['Date de publication'].dt.month
    df['Mois_Nom'] = df['Date de publication'].dt.month.map({
        1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril', 5: 'Mai', 6: 'Juin',
        7: 'Juillet', 8: 'Août', 9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
    })
    df['Année'] = df['Date de publication'].dt.year
    df['Gagné_bool'] = df['Statut'].apply(lambda x: 1 if x == 'Gagné' else 0)
    df['Score AO stratégique'] = df.apply(
        lambda row: (row['Montant estimé (MAD)'] * row['Gagné_bool']) / max(1, row['Complexité perçue (1-5)']), 
        axis=1
    )
    
    return df