import pandas as pd
import numpy as np
from pathlib import Path
import os
import json
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import ast
import umap
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# Configuration
# ==========================================
INPUT_META_FILE = "paperMerge.txt"       # JSON Lines 格式
INPUT_ENCODED_FILE = "paperMerge_encoded.tsv" # TSV 格式
OUTPUT_FOLDER = "realoutputs"

# Stage 3 Parameters
N_COMPONENTS = 256
N_CLUSTERS = 60

# Stage 6 Parameters
MACRO_CATEGORIES = ['A: Clinical', 'B: Method', 'C: Material', 'D: Basic Sci', 'E: Social']
FINE_AREAS_COUNT = 27

# Stage 8 Parameters
UMAP_N_NEIGHBORS = 15
UMAP_MIN_DIST = 0.1

# Stage 10 Parameters
STRUCTURE_ROLES = ['foundational', 'anchor_core', 'adjacent_method', 'adjacent_material', 
                   'adjacent_social', 'frontier', 'bridge', 'peripheral']

# Stage 11 Parameters
YEAR_CUTOFF = 2015
MIN_DOCS_FUTURE = 40
MIN_GROWTH_RATIO = 1.5

# Stage 12 Parameters
ANCHOR_MACRO = 'A: Clinical'  # 锚定领域宏观类别
ALIGNMENT_WEIGHTS = (0.5, 0.25, 0.25)  # (frontier, anchor_core, future_frontier)

# ==========================================
# Helper Functions
# ==========================================
def save_df_to_csv(df, filename, folder=OUTPUT_FOLDER):
    """保存 DataFrame 到 CSV 文件"""
    Path(folder).mkdir(parents=True, exist_ok=True)
    filepath = Path(folder) / filename
    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    print(f"Saved: {filepath}")

def load_keywords_mapping():
    """
    加载关键词到领域的映射规则
    返回一个字典，格式为 {macro: {fine_area: [keywords]}}
    """
    # 这里简化处理，实际应用中应该从配置文件加载
    mapping = {
        'A: Clinical': {
            'Rehabilitation': ['rehabilitation', 'rehab', 'therapy', 'clinical', 'patient'],
            'Assistive Technology': ['assistive', 'disability', 'wheelchair', 'prosthetic'],
            'Diagnosis': ['diagnosis', 'detection', 'screening', 'assessment'],
            'Treatment': ['treatment', 'intervention', 'management', 'care'],
            'Prevention': ['prevention', 'prophylaxis', 'risk reduction'],
            'Health Monitoring': ['monitoring', 'surveillance', 'tracking']
        },
        'B: Method': {
            'Machine Learning': ['machine learning', 'deep learning', 'neural network', 'ai'],
            'Signal Processing': ['signal processing', 'filtering', 'transform', 'analysis'],
            'Control Systems': ['control', 'feedback', 'pid', 'adaptive'],
            'Optimization': ['optimization', 'minimization', 'maximization'],
            'Data Analysis': ['data analysis', 'statistics', 'mining', 'analytics']
        },
        'C: Material': {
            'Biomaterials': ['biomaterial', 'biocompatible', 'tissue engineering'],
            'Nanomaterials': ['nanoparticle', 'nanotube', 'nanofiber'],
            'Smart Materials': ['smart material', 'shape memory', 'self-healing'],
            'Sensors': ['sensor', 'actuator', 'transducer', 'electrode'],
            'Wearable Devices': ['wearable', 'textile', 'flexible', 'portable']
        },
        'D: Basic Sci': {
            'Neuroscience': ['neuro', 'brain', 'neuron', 'cognitive'],
            'Biomechanics': ['biomechanics', 'kinematics', 'dynamics', 'muscle'],
            'Physiology': ['physiology', 'cardiovascular', 'respiratory', 'metabolism'],
            'Anatomy': ['anatomy', 'structure', 'organ', 'tissue'],
            'Genetics': ['genetic', 'gene', 'dna', 'rna', 'mutation']
        },
        'E: Social': {
            'Ethics': ['ethics', 'privacy', 'consent', 'regulation'],
            'Economics': ['cost', 'economic', 'reimbursement', 'market'],
            'Policy': ['policy', 'guideline', 'standard', 'regulation'],
            'User Experience': ['user experience', 'usability', 'acceptance', 'adoption'],
            'Education': ['education', 'training', 'learning', 'curriculum']
        }
    }
    return mapping

def classify_domain(text, mapping):
    """
    根据文本内容分类到宏观类别和细分领域
    """
    text_lower = text.lower()
    
    # 初始化结果
    macro = 'E: Social'  # 默认值
    fine_area = 'Other'  # 默认值
    
    # 查找匹配的宏观类别和细分领域
    max_matches = 0
    for m, areas in mapping.items():
        for area, keywords in areas.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches > max_matches:
                max_matches = matches
                macro = m
                fine_area = area
    
    return macro, fine_area

# ==========================================
# Stage 0: Data Alignment & Merging
# ==========================================
def generate_stage0_data():
    """
    Stage 0: 对齐并合并两个源文件。
    输出: stage0_merged_basic.csv
    """
    print(">>> Stage 0: Aligning and merging data...")
    
    # 1. 读取 Encoded TSV
    if not os.path.exists(INPUT_ENCODED_FILE):
        print(f"Error: {INPUT_ENCODED_FILE} not found.")
        return None
    df_enc = pd.read_csv(INPUT_ENCODED_FILE, sep='\t', encoding='utf-8')
    df_enc['row_id'] = df_enc.index
    print(f"  Loaded encoded TSV: {len(df_enc)} rows.")
    
    # 2. 读取 Meta JSON Lines
    if not os.path.exists(INPUT_META_FILE):
        print(f"Error: {INPUT_META_FILE} not found.")
        return None
    meta_data = []
    with open(INPUT_META_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                meta_data.append(json.loads(line))
            except:
                continue
    df_meta = pd.DataFrame(meta_data)
    df_meta['row_id'] = df_meta.index
    print(f"  Loaded meta JSON: {len(df_meta)} rows.")
    
    # 3. 对齐合并
    # 使用 row_id 进行 inner join
    df_merged = pd.merge(df_enc, df_meta, on='row_id', how='inner', suffixes=('_enc', '_meta'))
    print(f"  Merged table: {len(df_merged)} rows.")
    
    # 保存 Stage 0 结果
    save_df_to_csv(df_merged, "stage0_merged_basic.csv")
    return df_merged

# ==========================================
# Stage 1: Core Extraction & Cleaning
# ==========================================
def generate_stage1_data(df_stage0):
    """
    Stage 1: 提取核心字段，清洗文本，去重。
    输出: stage1_core_clean.csv
    """
    if df_stage0 is None: return None
    print(">>> Stage 1: Extracting core fields and cleaning...")
    
    # ==========================================
    # 1. 字段映射与提取
    # ==========================================
    
    # --- 标题提取 ---
    # 策略：优先使用 meta 文件的 title (字符串)，因为 encoded 文件的 title 是 int64 (可能是ID)
    if 'title_meta' in df_stage0.columns:
        df_stage0['title'] = df_stage0['title_meta'].fillna("").astype(str)
    elif 'title' in df_stage0.columns:
        # 检查类型，如果是 int64，说明是 encoded 文件的问题，置空或尝试从其他地方获取
        if df_stage0['title'].dtype == 'int64':
            print("  Warning: 'title' from encoded file is int64. Using empty string as fallback.")
            df_stage0['title'] = ""
        else:
            df_stage0['title'] = df_stage0['title'].fillna("").astype(str)
    else:
        df_stage0['title'] = ""

    # --- 摘要重建 (基于倒排索引) ---
    def reconstruct_abstract(row):
        """
        根据倒排索引重建摘要文本。
        
        参数:
            row: DataFrame的一行数据，包含 'abstract_inverted_index_meta' 或 'abstract_inverted_index_enc' 字段
            
        返回:
            str: 重建后的摘要文本
        """
        # 1. 尝试获取索引字段
        # Stage 0 合并后，meta 的列会带 _meta 后缀，enc 的列带 _enc 后缀
        idx = row.get('abstract_inverted_index_meta')
        
        # 如果 meta 没有或为空，尝试从 encoded 获取
        if pd.isna(idx) or idx == '' or idx == '/':
            idx = row.get('abstract_inverted_index_enc')
        
        # 2. 处理无效数据
        if pd.isna(idx) or idx == '' or idx == '/':
            return ""
        
        # 3. 如果已经是字符串形式的摘要（非字典），直接返回
        if isinstance(idx, str):
            # 检查是否看起来像字典（包含花括号）
            if '{' not in idx:
                return idx
            
            # 尝试解析字符串形式的字典
            try:
                idx_dict = ast.literal_eval(idx)
            except (ValueError, SyntaxError) as e:
                # 解析失败，返回空字符串
                print(f"Warning: Failed to parse abstract index string: {e}")
                return ""
            
            # 如果解析成功，继续处理字典
            idx = idx_dict
        
        # 4. 如果是字典，进行重建
        if isinstance(idx, dict):
            try:
                # 创建位置到单词的映射
                pos_word_map = {}
                
                for word, positions in idx.items():
                    # 确保 positions 是可迭代对象
                    if isinstance(positions, (list, tuple)):
                        for pos in positions:
                            # 确保位置是有效整数
                            if isinstance(pos, int) and pos >= 0:
                                pos_word_map[pos] = word
                    # 处理单个位置的情况（非列表）
                    elif isinstance(positions, int) and positions >= 0:
                        pos_word_map[positions] = word
                
                # 如果映射为空，返回空字符串
                if not pos_word_map:
                    return ""
                
                # 按位置排序并拼接单词
                sorted_positions = sorted(pos_word_map.keys())
                abstract = " ".join([pos_word_map[pos] for pos in sorted_positions])
                
                return abstract
            except Exception as e:
                # 处理重建过程中的任何异常
                print(f"Warning: Error reconstructing abstract from dictionary: {e}")
                return ""
        
        # 5. 如果既不是字符串也不是字典，返回空字符串
        return ""

    df_stage0['abstract_text'] = df_stage0.apply(reconstruct_abstract, axis=1)
    
    # 打印摘要还原统计
    print(f"  Abstract reconstruction stats:")
    print(f"    Total rows: {len(df_stage0)}")
    print(f"    Successfully reconstructed: {(df_stage0['abstract_text'].str.len() > 20).sum()}")
    print(f"    Failed or empty: {(df_stage0['abstract_text'].str.len() <= 20).sum()}")

    # ==========================================
    # 2. 语言过滤
    # ==========================================
    def is_english(text):
        return bool(re.search('[a-zA-Z]', text))
    
    mask_english = df_stage0['title'].apply(is_english) | df_stage0['abstract_text'].apply(is_english)
    df_stage0 = df_stage0[mask_english]
    print(f"  After language filter: {len(df_stage0)} rows.")

    # ==========================================
    # 3. 年份提取
    # ==========================================
    year_field = None
    for field in ['publication_year_meta', 'publication_year_enc', 'publication_year', 'year']:
        if field in df_stage0.columns:
            year_field = field
            break
    
    if year_field:
        print(f"  Found year field: {year_field}")
        # 尝试转换为数字
        df_stage0['year'] = pd.to_numeric(df_stage0[year_field], errors='coerce')
        
        # 检查年份范围
        if df_stage0['year'].notna().any():
            min_year = df_stage0['year'].min()
            max_year = df_stage0['year'].max()
            print(f"  Year range: {min_year} - {max_year}")
            
            # 简单的合理性过滤 (1900-Current Year + 1)
            current_year = pd.Timestamp.now().year + 1
            valid_years_mask = df_stage0['year'].notna() & (df_stage0['year'] >= 1900) & (df_stage0['year'] <= current_year)
            
            # 如果大量年份异常，尝试从 created_date 提取
            if valid_years_mask.sum() < len(df_stage0) * 0.5:
                print("  Warning: More than 50% of records have invalid years. Trying created_date...")
                if 'created_date_meta' in df_stage0.columns:
                    # meta 中的 created_date 是字符串 "2025-10-10T..."
                    df_stage0['created_date_parsed'] = pd.to_datetime(df_stage0['created_date_meta'], errors='coerce')
                    df_stage0['year_from_created'] = df_stage0['created_date_parsed'].dt.year
                    df_stage0['year'] = df_stage0['year_from_created'].combine_first(df_stage0['year'])
            
            # 最终过滤
            valid_years_mask = df_stage0['year'].notna() & (df_stage0['year'] >= 1900) & (df_stage0['year'] <= current_year)
            print(f"  Records with valid years: {valid_years_mask.sum()}")
            df_stage0 = df_stage0[valid_years_mask]
    else:
        print("  Warning: No year field found. Setting default year to 2020.")
        df_stage0['year'] = 2020

    # ==========================================
    # 4. 去重
    # ==========================================
    # 规范化标题用于去重
    df_stage0['title_norm'] = df_stage0['title'].str.lower().str.strip()
    
    # DOI 清洗与提取
    doi_clean = ""
    if 'doi_meta' in df_stage0.columns:
        doi_clean = df_stage0['doi_meta'].fillna("").astype(str).str.lower().str.strip()
    elif 'doi_enc' in df_stage0.columns:
        doi_clean = df_stage0['doi_enc'].fillna("").astype(str).str.lower().str.strip()
    
    # 去除无效 DOI 标记
    df_stage0['doi_clean'] = doi_clean.replace('nan', '').replace('none', '').replace('/', '')
    
    # 定义去重键：如果有有效DOI，用DOI；否则用规范化标题
    df_stage0['dedup_key'] = df_stage0['doi_clean'].where(
        df_stage0['doi_clean'] != "", 
        df_stage0['title_norm']
    )
    
    # 保留每个键的第一条记录
    initial_count = len(df_stage0)
    df_stage0 = df_stage0.drop_duplicates(subset=['dedup_key'], keep='first')
    print(f"  After deduplication: {len(df_stage0)} rows (removed {initial_count - len(df_stage0)} duplicates).")

    # ==========================================
    # 5. 删除无文本信息行
    # ==========================================
    mask_has_text = (df_stage0['title'].str.len() > 0) | (df_stage0['abstract_text'].str.len() > 0)
    df_stage0 = df_stage0[mask_has_text]
    print(f"  After removing empty text: {len(df_stage0)} rows.")

    # ==========================================
    # 6. 构造 full_text_clean
    # ==========================================
    # 简单拼接
    df_stage0['full_text_raw'] = df_stage0['title'] + ". " + df_stage0['abstract_text']
    
    # 清洗：换行符、多空格、小写
    df_stage0['full_text_clean'] = df_stage0['full_text_raw'].str.replace(r'\n+', ' ', regex=True)
    df_stage0['full_text_clean'] = df_stage0['full_text_clean'].str.replace(r'\s+', ' ', regex=True)
    df_stage0['full_text_clean'] = df_stage0['full_text_clean'].str.strip().str.lower()
    
    # 保存 Stage 1 结果
    save_df_to_csv(df_stage0, "stage1_core_clean.csv")
    return df_stage0



# ==========================================
# Stage 2: Text Reconstruction & Cleaning
# ==========================================
def generate_stage2_data(df_stage1):
    """
    Stage 2: 文本重建与清洗
    输出: stage2_text_reconstructed.csv
    """
    if df_stage1 is None: return None
    print(">>> Stage 2: Text reconstruction and cleaning...")
    
    # 1. 关键词解析
    def parse_keywords(keywords):
        # 处理None或NaN值
        if keywords is None or (isinstance(keywords, float) and np.isnan(keywords)):
            return ""
        
        # 如果是列表
        if isinstance(keywords, list):
            return "; ".join([str(k) for k in keywords])
        
        # 如果是字符串
        keywords_str = str(keywords)
        
        # 检查是否为空字符串或无效标记
        if keywords_str.lower() in ['nan', 'none', '', '/']:
            return ""
        
        # 尝试解析字符串化的列表
        if keywords_str.startswith('[') and keywords_str.endswith(']'):
            try:
                keywords_list = ast.literal_eval(keywords_str)
                if isinstance(keywords_list, list):
                    return "; ".join([str(k) for k in keywords_list])
            except:
                pass
        
        # 直接返回字符串，去掉无效标记
        return keywords_str.replace('nan', '').replace('None', '').replace('/', '').strip()
    
    # 尝试从多个可能的字段中提取关键词
    keywords_field = None
    for field in ['keywords_meta', 'keywords_enc', 'keywords']:
        if field in df_stage1.columns:
            keywords_field = field
            break
    
    if keywords_field:
        # 打印关键词字段的信息
        print(f"  Found keywords field: {keywords_field}")
        print(f"  Keywords field data type: {df_stage1[keywords_field].dtype}")
        print(f"  Keywords field sample values:")
        print(df_stage1[keywords_field].head(5))
        
        df_stage1['keywords_text'] = df_stage1[keywords_field].apply(parse_keywords)
    else:
        print("  Warning: No keywords field found in data")
        df_stage1['keywords_text'] = ""
    
    # 2. 构造 full_text_clean
    df_stage1['full_text_clean'] = (
        df_stage1['title'] + ". " + 
        df_stage1['abstract_text'] + ". " + 
        df_stage1['keywords_text']
    )
    
    # 3. 清洗文本
    df_stage1['full_text_clean'] = df_stage1['full_text_clean'].str.replace(r'\n+', ' ', regex=True)
    df_stage1['full_text_clean'] = df_stage1['full_text_clean'].str.replace(r'\s+', ' ', regex=True)
    df_stage1['full_text_clean'] = df_stage1['full_text_clean'].str.strip().str.lower()
    
    # 保存 Stage 2 结果
    save_df_to_csv(df_stage1, "stage2_text_reconstructed.csv")
    return df_stage1

# ==========================================
# Stage 3: Embedding (TF-IDF + SVD)
# ==========================================
def generate_stage3_data(df_stage2):
    """
    Stage 3: 计算语义向量。
    输出: stage3_embeddings.csv (包含 doc_id 和 vector)
    """
    if df_stage2 is None: return None
    print(">>> Stage 3: Computing TF-IDF and SVD embeddings...")
    
    # 1. TF-IDF
    vectorizer = TfidfVectorizer(max_features=20000, stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(df_stage2['full_text_clean'])
    print(f"  TF-IDF Matrix shape: {tfidf_matrix.shape}")
    
    # 2. SVD (LSA)
    svd = TruncatedSVD(n_components=N_COMPONENTS, random_state=42)
    embeddings = svd.fit_transform(tfidf_matrix)
    print(f"  SVD Embeddings shape: {embeddings.shape}")
    
    # 3. 保存结果
    # 为了节省空间，只保存 doc_id 和 embedding (作为列表字符串存储，或者单独存 npy)
    # 这里我们存为 CSV，将向量转为字符串
    df_embeddings = pd.DataFrame({
        'doc_id': df_stage2.index, # 使用 index 作为 doc_id
        'embedding': [vec.tolist() for vec in embeddings]
    })
    save_df_to_csv(df_embeddings, "stage3_embeddings.csv")
    
    return df_embeddings, vectorizer, svd

# ==========================================
# Stage 4: Clustering (MiniBatchKMeans)
# ==========================================
def generate_stage4_data(df_embeddings):
    """
    Stage 4: 聚类。
    输出: stage4_clusters.csv (包含 doc_id 和 cluster_id)
    """
    if df_embeddings is None: return None
    print(">>> Stage 4: Clustering with MiniBatchKMeans...")
    
    # 1. 准备向量矩阵
    vectors = np.array(df_embeddings['embedding'].tolist())
    
    # 2. 聚类
    kmeans = MiniBatchKMeans(n_clusters=N_CLUSTERS, random_state=42, batch_size=2048)
    clusters = kmeans.fit_predict(vectors)
    print(f"  Clustered into {N_CLUSTERS} groups.")
    
    # 3. 保存结果
    df_clusters = pd.DataFrame({
        'doc_id': df_embeddings['doc_id'],
        'cluster_id': clusters
    })
    save_df_to_csv(df_clusters, "stage4_clusters.csv")
    
    return df_clusters, kmeans

# ==========================================
# Stage 5: Topic Naming & Aggregation
# ==========================================
def generate_stage5_data(df_stage2, df_clusters, vectorizer):
    """
    Stage 5: 生成簇级信息。
    输出: stage5_topic_clusters.csv (包含 cluster_id, top_terms, sample_titles 等)
    """
    if df_stage2 is None or df_clusters is None: return None
    print(">>> Stage 5: Generating topic names and aggregating...")
    
    # 1. 将聚类结果合并回文档表
    df_merged = df_stage2.merge(df_clusters, left_index=True, right_on='doc_id')
    
    # 2. 提取年份
    if 'year' in df_merged.columns:
        df_merged['year'] = pd.to_numeric(df_merged['year'], errors='coerce')
    else:
        df_merged['year'] = 0 # 默认值
    
    # 3. 计算每个簇的统计信息
    cluster_stats = []
    
    # 获取特征词名称
    feature_names = vectorizer.get_feature_names_out()
    
    for c_id in range(N_CLUSTERS):
        cluster_docs = df_merged[df_merged['cluster_id'] == c_id]
        
        if len(cluster_docs) == 0:
            continue
            
        # A. Top Terms (基于 TF-IDF 平均值)
        # 重新计算该簇的 TF-IDF
        corpus = cluster_docs['full_text_clean'].tolist()
        tfidf_c = vectorizer.transform(corpus)
        mean_tfidf = np.mean(tfidf_c.toarray(), axis=0)
        
        # 获取得分最高的 3 个词的索引
        top_indices = mean_tfidf.argsort()[-3:][::-1]
        top_terms = ", ".join([feature_names[i] for i in top_indices])
        
        # B. Sample Titles (取前3个)
        titles = cluster_docs['title'].head(3).tolist()
        sample_titles = "; ".join([str(t) for t in titles])
        
        # C. 时间分布
        years = cluster_docs['year'].values
        pre2010 = np.sum(years < 2010)
        y_10_15 = np.sum((years >= 2010) & (years < 2016))
        y_16_20 = np.sum((years >= 2016) & (years < 2021))
        y_21_plus = np.sum(years >= 2021)
        
        cluster_stats.append({
            'cluster_id': c_id,
            'cluster_name': f"Topic {c_id}", # 初始命名
            'top_terms': top_terms,
            'sample_titles': sample_titles,
            'total_docs': len(cluster_docs),
            'pre2010': pre2010,
            '2010_2015': y_10_15,
            '2016_2020': y_16_20,
            '2021plus': y_21_plus
        })
    
    df_topic_clusters = pd.DataFrame(cluster_stats)
    save_df_to_csv(df_topic_clusters, "stage5_topic_clusters.csv")
    
    return df_topic_clusters

# ==========================================
# Stage 6: Semantic Hierarchy & 27 Fine Areas
# ==========================================
def generate_stage6_data(df_stage2, df_clusters, df_topic_clusters):
    """
    Stage 6: 语义层级与27个细分领域
    输出: stage6_semantic_hierarchy.csv
    """
    if df_stage2 is None or df_clusters is None or df_topic_clusters is None: 
        return None
    print(">>> Stage 6: Building semantic hierarchy with 27 fine areas...")
    
    # 1. 加载关键词映射
    mapping = load_keywords_mapping()
    
    # 2. 将聚类结果合并回文档表
    df_merged = df_stage2.merge(df_clusters, left_index=True, right_on='doc_id')
    
    # 3. 为每个文档分类宏观类别和细分领域
    df_merged['macro'] = ''
    df_merged['fine_area'] = ''
    
    for idx, row in df_merged.iterrows():
        text = row['full_text_clean']
        macro, fine_area = classify_domain(text, mapping)
        df_merged.at[idx, 'macro'] = macro
        df_merged.at[idx, 'fine_area'] = fine_area
    
    # 4. 聚合到聚类级别
    cluster_macro = {}
    cluster_fine = {}
    
    for c_id in range(N_CLUSTERS):
        cluster_docs = df_merged[df_merged['cluster_id'] == c_id]
        
        if len(cluster_docs) == 0:
            continue
            
        # 找到最常见的宏观类别和细分领域
        macro_counts = cluster_docs['macro'].value_counts()
        fine_counts = cluster_docs['fine_area'].value_counts()
        
        cluster_macro[c_id] = macro_counts.index[0] if len(macro_counts) > 0 else 'E: Social'
        cluster_fine[c_id] = fine_counts.index[0] if len(fine_counts) > 0 else 'Other'
    
    # 5. 更新聚类表
    df_topic_clusters['macro'] = df_topic_clusters['cluster_id'].map(cluster_macro)
    df_topic_clusters['fine_area'] = df_topic_clusters['cluster_id'].map(cluster_fine)
    
    # 6. 为细分领域分配唯一ID
    fine_areas = df_topic_clusters['fine_area'].unique()
    fine_area_to_id = {area: i+1 for i, area in enumerate(fine_areas)}
    df_topic_clusters['fine_area_id'] = df_topic_clusters['fine_area'].map(fine_area_to_id)
    
    # 保存 Stage 6 结果
    save_df_to_csv(df_topic_clusters, "stage6_semantic_hierarchy.csv")
    
    return df_topic_clusters

# ==========================================
# Stage 7: Time Trends Analysis
# ==========================================
def generate_stage7_data(df_topic_clusters):
    """
    Stage 7: 聚类与领域的时间趋势
    输出: stage7_time_trends.csv
    """
    if df_topic_clusters is None: 
        return None
    print(">>> Stage 7: Analyzing time trends...")
    
    # 1. 计算每个聚类的时间统计
    df_topic_clusters['total_docs'] = (
        df_topic_clusters['pre2010'] + 
        df_topic_clusters['2010_2015'] + 
        df_topic_clusters['2016_2020'] + 
        df_topic_clusters['2021plus']
    )
    
    # 2. 计算近期占比 (2016+)
    df_topic_clusters['recent_share_2016plus'] = (
        (df_topic_clusters['2016_2020'] + df_topic_clusters['2021plus']) / 
        df_topic_clusters['total_docs']
    ).fillna(0)
    
    # 3. 计算增长率 (2010-2015 vs 2016-2020)
    df_topic_clusters['growth_ratio'] = np.where(
        df_topic_clusters['2010_2015'] > 0,
        (df_topic_clusters['2016_2020'] - df_topic_clusters['2010_2015']) / df_topic_clusters['2010_2015'],
        0
    )
    
    # 4. 计算领域级时间统计
    df_fine_trends = df_topic_clusters.groupby('fine_area').agg({
        'total_docs': 'sum',
        'pre2010': 'sum',
        '2010_2015': 'sum',
        '2016_2020': 'sum',
        '2021plus': 'sum'
    }).reset_index()
    
    df_fine_trends['recent_share_2016plus'] = (
        (df_fine_trends['2016_2020'] + df_fine_trends['2021plus']) / 
        df_fine_trends['total_docs']
    ).fillna(0)
    
    # 保存 Stage 7 结果
    save_df_to_csv(df_topic_clusters, "stage7_cluster_time_trends.csv")
    save_df_to_csv(df_fine_trends, "stage7_fine_area_time_trends.csv")
    
    return df_topic_clusters, df_fine_trends

# ==========================================
# Stage 8: 2D Knowledge Map
# ==========================================
def generate_stage8_data(df_embeddings, df_clusters, df_topic_clusters):
    """
    Stage 8: 二维多领域知识地图
    输出: stage8_2d_map.csv
    """
    if df_embeddings is None or df_clusters is None or df_topic_clusters is None: 
        return None
    print(">>> Stage 8: Generating 2D knowledge map...")
    
    # 1. 准备向量矩阵
    vectors = np.array(df_embeddings['embedding'].tolist())
    
    # 2. 计算每个聚类的中心向量
    cluster_centers = {}
    for c_id in range(N_CLUSTERS):
        cluster_docs = df_clusters[df_clusters['cluster_id'] == c_id]
        if len(cluster_docs) > 0:
            cluster_vectors = vectors[cluster_docs.index]
            cluster_centers[c_id] = np.mean(cluster_vectors, axis=0)
    
    # 3. 使用UMAP降维到2D
    centers_matrix = np.array([cluster_centers[c_id] for c_id in range(N_CLUSTERS)])
    
    reducer = umap.UMAP(
        n_neighbors=UMAP_N_NEIGHBORS,
        min_dist=UMAP_MIN_DIST,
        n_components=2,
        random_state=42
    )
    
    embedding_2d = reducer.fit_transform(centers_matrix)
    
    # 4. 将2D坐标添加到聚类表
    df_topic_clusters['map_x'] = embedding_2d[:, 0]
    df_topic_clusters['map_y'] = embedding_2d[:, 1]
    
    # 保存 Stage 8 结果
    save_df_to_csv(df_topic_clusters, "stage8_2d_map.csv")
    
    return df_topic_clusters

# ==========================================
# Stage 9: Domain Coverage & Time Horizon
# ==========================================
def generate_stage9_data(df_topic_clusters, df_fine_trends):
    """
    Stage 9: 细分领域的覆盖度与时间视野
    输出: stage9_domain_coverage.csv
    """
    if df_topic_clusters is None or df_fine_trends is None: 
        return None
    print(">>> Stage 9: Analyzing domain coverage and time horizon...")
    
    # 1. 为每个领域分类状态
    def classify_domain_state(row):
        if row['recent_share_2016plus'] > 0.7 and row['total_docs'] < 100:
            return 'Emerging'
        elif row['recent_share_2016plus'] > 0.5 and row['total_docs'] >= 100:
            return 'Growing Mainstream'
        elif row['recent_share_2016plus'] <= 0.5 and row['total_docs'] >= 200:
            return 'Mature'
        else:
            return 'Other'
    
    df_fine_trends['domain_state'] = df_fine_trends.apply(classify_domain_state, axis=1)
    
    # 2. 计算领域覆盖度
    total_docs = df_fine_trends['total_docs'].sum()
    df_fine_trends['domain_coverage'] = df_fine_trends['total_docs'] / total_docs
    
    # 保存 Stage 9 结果
    save_df_to_csv(df_fine_trends, "stage9_domain_coverage.csv")
    
    return df_fine_trends

# ==========================================
# Stage 10: Three-Layer Features & Structure Roles
# ==========================================
def generate_stage10_data(df_topic_clusters):
    """
    Stage 10: 三层特征与多领域结构角色
    输出: stage10_structure_roles.csv
    """
    if df_topic_clusters is None: 
        return None
    print(">>> Stage 10: Building three-layer features and structure roles...")
    
    # 1. 构建三层特征
    # 语义层 (x_sem)
    macro_dummies = pd.get_dummies(df_topic_clusters['macro'], prefix='macro')
    fine_area_dummies = pd.get_dummies(df_topic_clusters['fine_area'], prefix='fine_area')
    
    # 从top_terms中提取关键词特征
    top_terms_features = pd.DataFrame()
    for term in ['robot', 'learning', 'material', 'social', 'clinical', 'sensor']:
        top_terms_features[f'has_{term}'] = df_topic_clusters['top_terms'].str.contains(term, case=False).astype(int)
    
    x_sem = pd.concat([macro_dummies, fine_area_dummies, top_terms_features], axis=1)
    
    # 深结构层 (x_deep)
    df_topic_clusters['size_log'] = np.log1p(df_topic_clusters['total_docs'])
    x_deep = df_topic_clusters[['map_x', 'map_y', 'size_log']].copy()
    
    # 认知层 (x_cog)
    # 时间分箱
    def bin_value(value, bins, labels):
        for i, (lower, upper) in enumerate(bins):
            if lower <= value < upper:
                return labels[i]
        return labels[-1]  # 默认最后一个区间
    
    # 计算分位数
    recent_share_bins = [
        (0, df_topic_clusters['recent_share_2016plus'].quantile(0.33)),
        (df_topic_clusters['recent_share_2016plus'].quantile(0.33), df_topic_clusters['recent_share_2016plus'].quantile(0.67)),
        (df_topic_clusters['recent_share_2016plus'].quantile(0.67), 1.01)
    ]
    recent_share_labels = ['low', 'medium', 'high']
    
    df_topic_clusters['recent_share_bin'] = df_topic_clusters['recent_share_2016plus'].apply(
        lambda x: bin_value(x, recent_share_bins, recent_share_labels)
    )
    
    # 大小分箱
    size_bins = [
        (0, df_topic_clusters['size_log'].quantile(0.33)),
        (df_topic_clusters['size_log'].quantile(0.33), df_topic_clusters['size_log'].quantile(0.67)),
        (df_topic_clusters['size_log'].quantile(0.67), 100)
    ]
    size_labels = ['small', 'medium', 'large']
    
    df_topic_clusters['size_bin'] = df_topic_clusters['size_log'].apply(
        lambda x: bin_value(x, size_bins, size_labels)
    )
    
    # 转换为one-hot
    recent_share_dummies = pd.get_dummies(df_topic_clusters['recent_share_bin'], prefix='recent_share')
    size_dummies = pd.get_dummies(df_topic_clusters['size_bin'], prefix='size')
    
    x_cog = pd.concat([recent_share_dummies, size_dummies], axis=1)
    
    # 合并三层特征
    x_all = pd.concat([x_sem, x_deep, x_cog], axis=1)
    
    # 2. 训练结构角色分类器
    # 这里我们使用简单的规则生成标签，实际应用中应该使用人工标注
    def assign_structure_role(row):
        if row['macro'] == 'A: Clinical' and row['size_bin'] == 'large':
            return 'anchor_core'
        elif row['macro'] == 'B: Method' and row['recent_share_bin'] == 'high':
            return 'adjacent_method'
        elif row['macro'] == 'C: Material' and row['recent_share_bin'] == 'high':
            return 'adjacent_material'
        elif row['macro'] == 'E: Social':
            return 'adjacent_social'
        elif row['recent_share_bin'] == 'high' and row['size_bin'] == 'small':
            return 'frontier'
        elif row['size_bin'] == 'medium':
            return 'bridge'
        else:
            return 'peripheral'
    
    df_topic_clusters['structure_role'] = df_topic_clusters.apply(assign_structure_role, axis=1)
    
    # 保存 Stage 10 结果
    save_df_to_csv(df_topic_clusters, "stage10_structure_roles.csv")
    
    return df_topic_clusters, x_all

# ==========================================
# Stage 11: Future Frontier Prediction
# ==========================================
def generate_stage11_data(df_stage2, df_clusters, df_topic_clusters):
    """
    Stage 11: 多领域未来前沿预测
    输出: stage11_frontier_prediction.csv
    """
    if df_stage2 is None or df_clusters is None or df_topic_clusters is None: 
        return None
    print(">>> Stage 11: Predicting future frontiers...")
    
    # 1. 将聚类结果合并回文档表
    df_merged = df_stage2.merge(df_clusters, left_index=True, right_on='doc_id')
    
    # 2. 提取年份
    # 使用在Stage 1中已经提取的year字段
    if 'year' in df_merged.columns:
        print(f"  Using 'year' column with {df_merged['year'].notna().sum()} non-null values")
        df_merged['year'] = pd.to_numeric(df_merged['year'], errors='coerce')
    else:
        print("  Warning: No year column found in data")
        return None
    
    # 打印年份统计信息
    print(f"  Year statistics:")
    print(f"    Non-null years: {df_merged['year'].notna().sum()}")
    print(f"    Year range: {df_merged['year'].min()} - {df_merged['year'].max()}")
    print(f"    Year distribution:\n{df_merged['year'].value_counts().sort_index().head(10)}")
    
    # 3. 计算每个聚类在过去和未来的文献量
    cluster_stats = []
    
    for c_id in range(N_CLUSTERS):
        cluster_docs = df_merged[df_merged['cluster_id'] == c_id]
        
        if len(cluster_docs) == 0:
            continue
            
        # 过滤年份
        valid_years = cluster_docs[cluster_docs['year'] > 0]['year'].values
        
        if len(valid_years) == 0:
            print(f"  Cluster {c_id}: No valid years found")
            # 添加默认值，避免后续错误
            cluster_stats.append({
                'cluster_id': c_id,
                'docs_past': 10,  # 默认值
                'docs_future': 5,  # 默认值
                'growth_ratio': 0.5,  # 默认值
                'is_frontier': False  # 默认值
            })
            continue
            
        # 计算过去和未来的文献量
        docs_past = np.sum(valid_years <= YEAR_CUTOFF)
        docs_future = np.sum(valid_years > YEAR_CUTOFF)
        
        # 计算增长比
        growth_ratio = (docs_future + 1) / (docs_past + 1)
        
        # 判断是否为未来前沿
        is_frontier = (docs_future >= MIN_DOCS_FUTURE) and (growth_ratio >= MIN_GROWTH_RATIO)
        
        cluster_stats.append({
            'cluster_id': c_id,
            'docs_past': docs_past,
            'docs_future': docs_future,
            'growth_ratio': growth_ratio,
            'is_frontier': is_frontier
        })
    
    # 检查cluster_stats是否为空
    if not cluster_stats:
        print("  Warning: No valid clusters found for frontier prediction")
        # 创建一个默认的DataFrame，避免后续错误
        df_frontier = pd.DataFrame(columns=['cluster_id', 'docs_past', 'docs_future', 'growth_ratio', 'is_frontier'])
    else:
        df_frontier = pd.DataFrame(cluster_stats)
        print(f"  Processed {len(df_frontier)} clusters for frontier prediction")
        
        # 打印前沿统计信息
        frontier_count = df_frontier['is_frontier'].sum()
        print(f"  Found {frontier_count} frontier clusters")
    
    # 4. 训练未来前沿预测模型
    # 检查是否有足够的数据训练模型
    if len(df_frontier) < 10 or df_frontier['is_frontier'].sum() < 2:
        print("  Warning: Insufficient data for training frontier prediction model")
        print("  Using rule-based approach instead")
        
        # 使用基于规则的方法
        # 根据增长率和近期文献量分配前沿概率
        df_frontier['frontier_probability'] = 0.5  # 默认值
        
        # 高增长率和近期文献量高的聚类获得更高的前沿概率
        high_growth = df_frontier['growth_ratio'] > 1.5
        high_recent = df_frontier['docs_future'] > 20
        
        df_frontier.loc[high_growth & high_recent, 'frontier_probability'] = 0.8
        df_frontier.loc[high_growth & ~high_recent, 'frontier_probability'] = 0.6
        df_frontier.loc[~high_growth & high_recent, 'frontier_probability'] = 0.4
        
        # 5. 将预测结果合并到聚类表
        df_topic_clusters = df_topic_clusters.merge(
            df_frontier[['cluster_id', 'is_frontier', 'frontier_probability']],
            on='cluster_id',
            how='left'
        )
    else:
        # 准备特征
        X = df_frontier[['docs_past', 'growth_ratio']].values
        y = df_frontier['is_frontier'].astype(int).values
        
        # 训练随机森林分类器
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(X, y)
        
        # 预测未来前沿概率
        # 检查分类器是否有两个类别
        if len(rf.classes_) == 2:
            df_frontier['frontier_probability'] = rf.predict_proba(X)[:, 1]
        else:
            # 如果只有一个类别，使用基于规则的方法
            print("  Warning: Only one class in training data, using rule-based approach")
            df_frontier['frontier_probability'] = 0.5  # 默认值
            
            # 高增长率和近期文献量高的聚类获得更高的前沿概率
            high_growth = df_frontier['growth_ratio'] > 1.5
            high_recent = df_frontier['docs_future'] > 20
            
            df_frontier.loc[high_growth & high_recent, 'frontier_probability'] = 0.8
            df_frontier.loc[high_growth & ~high_recent, 'frontier_probability'] = 0.6
            df_frontier.loc[~high_growth & high_recent, 'frontier_probability'] = 0.4
        
        # 5. 将预测结果合并到聚类表
        df_topic_clusters = df_topic_clusters.merge(
            df_frontier[['cluster_id', 'is_frontier', 'frontier_probability']],
            on='cluster_id',
            how='left'
        )
    
    # 保存 Stage 11 结果
    save_df_to_csv(df_topic_clusters, "stage11_frontier_prediction.csv")
    
    return df_topic_clusters, None  # 返回None作为rf，因为没有训练有效的模型

# ==========================================
# Stage 12: Anchor Alignment & Frontier Potential
# ==========================================
def generate_stage12_data(df_topic_clusters):
    """
    Stage 12: 锚定领域对齐度、前沿潜力与多领域路线图
    输出: stage12_alignment_frontier.csv
    """
    if df_topic_clusters is None: 
        return None
    print(">>> Stage 12: Calculating anchor alignment and frontier potential...")
    
    # 1. 计算锚定领域对齐度
    # 找到锚定领域的核心聚类
    anchor_clusters = df_topic_clusters[df_topic_clusters['macro'] == ANCHOR_MACRO]
    
    if len(anchor_clusters) > 0:
        # 计算锚定领域核心的平均坐标
        anchor_center_x = anchor_clusters['map_x'].mean()
        anchor_center_y = anchor_clusters['map_y'].mean()
        
        # 计算每个聚类与锚定领域核心的距离
        df_topic_clusters['dist_to_anchor'] = np.sqrt(
            (df_topic_clusters['map_x'] - anchor_center_x)**2 + 
            (df_topic_clusters['map_y'] - anchor_center_y)**2
        )
        
        # 归一化距离到[0, 1]范围，然后转换为对齐度
        d_min = df_topic_clusters['dist_to_anchor'].min()
        d_max = df_topic_clusters['dist_to_anchor'].max()
        
        df_topic_clusters['alignment_score'] = 1 - (df_topic_clusters['dist_to_anchor'] - d_min) / (d_max - d_min)
    else:
        df_topic_clusters['alignment_score'] = 0.5  # 默认值
    
    # 2. 计算前沿潜力
    # 获取结构角色概率（这里简化处理，使用one-hot编码）
    role_dummies = pd.get_dummies(df_topic_clusters['structure_role'], prefix='role')
    
    # 获取前沿概率
    frontier_prob = df_topic_clusters['frontier_probability'].fillna(0)
    
    # 获取锚定核心概率（这里简化处理，使用macro是否为锚定领域）
    anchor_core_prob = (df_topic_clusters['macro'] == ANCHOR_MACRO).astype(float)
    
    # 计算综合前沿潜力
    df_topic_clusters['frontier_potential'] = (
        ALIGNMENT_WEIGHTS[0] * frontier_prob +
        ALIGNMENT_WEIGHTS[1] * anchor_core_prob +
        ALIGNMENT_WEIGHTS[2] * (df_topic_clusters['growth_ratio'] if 'growth_ratio' in df_topic_clusters.columns else 0)
    )
    
    # 归一化前沿潜力到[0, 1]范围
    f_min = df_topic_clusters['frontier_potential'].min()
    f_max = df_topic_clusters['frontier_potential'].max()
    df_topic_clusters['frontier_potential'] = (df_topic_clusters['frontier_potential'] - f_min) / (f_max - f_min)
    
    # 3. 定义多领域路线图类别
    def assign_roadmap_category(row):
        alignment = row['alignment_score']
        frontier = row['frontier_potential']
        is_anchor = row['macro'] == ANCHOR_MACRO
        is_frontier = row['is_frontier']
        is_bridge = row['structure_role'] == 'bridge'
        
        if is_anchor and frontier > 0.7:
            return 'anchor_core_growth_engine'
        elif is_anchor and frontier > 0.4:
            return 'anchor_core_stable_pillar'
        elif is_anchor:
            return 'anchor_clinical_pillar_stable'
        elif alignment > 0.6 and frontier > 0.6:
            return 'adjacent_method/material/social_frontier'
        elif alignment > 0.6:
            return 'adjacent_mature'
        elif frontier > 0.7:
            return 'enabling_material_frontier' if row['macro'] == 'C: Material' else 'generic_method_frontier'
        elif frontier > 0.5:
            return 'external_frontier'
        elif is_bridge:
            return 'strategic_bridge_stable'
        else:
            return 'peripheral_or_noise'
    
    df_topic_clusters['roadmap_category'] = df_topic_clusters.apply(assign_roadmap_category, axis=1)
    
    # 保存 Stage 12 结果
    save_df_to_csv(df_topic_clusters, "stage12_alignment_frontier.csv")
    
    return df_topic_clusters

# ==========================================
# Stage 13: 3×3 SAI Strategic Matrix
# ==========================================
def generate_stage13_data(df_topic_clusters):
    """
    Stage 13: 3×3 SAI 战略矩阵
    输出: stage13_strategic_matrix.csv
    """
    if df_topic_clusters is None: 
        return None
    print(">>> Stage 13: Building 3×3 SAI strategic matrix...")
    
    # 1. 计算对齐度和前沿潜力的分位数
    align_low = df_topic_clusters['alignment_score'].quantile(0.33)
    align_high = df_topic_clusters['alignment_score'].quantile(0.67)
    
    frontier_low = df_topic_clusters['frontier_potential'].quantile(0.33)
    frontier_high = df_topic_clusters['frontier_potential'].quantile(0.67)
    
    # 2. 分箱函数
    def bin_alignment(score):
        if score < align_low:
            return 'low'
        elif score >= align_high:
            return 'high'
        else:
            return 'medium'
    
    def bin_frontier(score):
        if score < frontier_low:
            return 'low'
        elif score >= frontier_high:
            return 'high'
        else:
            return 'medium'
    
    # 3. 应用分箱
    df_topic_clusters['alignment_bin'] = df_topic_clusters['alignment_score'].apply(bin_alignment)
    df_topic_clusters['frontier_bin'] = df_topic_clusters['frontier_potential'].apply(bin_frontier)
    
    # 4. 定义战略标签
    def assign_strategic_label(row):
        align = row['alignment_bin']
        frontier = row['frontier_bin']
        
        if align == 'high' and frontier == 'high':
            return 'priority_anchor_frontier'
        elif align == 'high' and frontier == 'medium':
            return 'core_anchor_consolidate'
        elif align == 'high' and frontier == 'low':
            return 'anchor_clinical_pillar_stable'
        elif align == 'medium' and frontier == 'high':
            return 'bridge_anchor_to_frontier'
        elif align == 'medium' and frontier == 'medium':
            return 'adjacent_mature'
        elif align == 'medium' and frontier == 'low':
            return 'adjacent_background'
        elif align == 'low' and frontier == 'high':
            return 'external_frontier_watchpoint'
        elif align == 'low' and frontier == 'medium':
            return 'external_mature_infrastructure'
        else:  # low, low
            return 'peripheral_or_legacy'
    
    df_topic_clusters['sai_strategy_label'] = df_topic_clusters.apply(assign_strategic_label, axis=1)
    
    # 5. 统计每个战略类别的聚类数量
    strategy_counts = df_topic_clusters['sai_strategy_label'].value_counts().reset_index()
    strategy_counts.columns = ['sai_strategy_label', 'count']
    
    # 6. 创建3x3矩阵
    matrix_data = []
    for align in ['low', 'medium', 'high']:
        for frontier in ['low', 'medium', 'high']:
            subset = df_topic_clusters[
                (df_topic_clusters['alignment_bin'] == align) & 
                (df_topic_clusters['frontier_bin'] == frontier)
            ]
            
            if len(subset) > 0:
                # 找到最常见的战略标签
                top_label = subset['sai_strategy_label'].value_counts().index[0]
                count = len(subset)
                
                # 获取代表性聚类
                if len(subset) >= 3:
                    sample_clusters = subset.nlargest(3, 'total_docs')['cluster_id'].tolist()
                else:
                    sample_clusters = subset['cluster_id'].tolist()
            else:
                top_label = 'empty'
                count = 0
                sample_clusters = []
            
            matrix_data.append({
                'alignment_bin': align,
                'frontier_bin': frontier,
                'strategy_label': top_label,
                'count': count,
                'sample_clusters': sample_clusters
            })
    
    df_matrix = pd.DataFrame(matrix_data)
    
    # 保存 Stage 13 结果
    save_df_to_csv(df_topic_clusters, "stage13_strategic_matrix_clusters.csv")
    save_df_to_csv(df_matrix, "stage13_strategic_matrix.csv")
    
    return df_topic_clusters, df_matrix

# ==========================================
# Main Execution
# ==========================================
def main():
    print(">>> 开始生成 Nature Protocols 投稿所需数据文件 (基于真实输入)...")
    
    # Stage 0
    df_stage0 = generate_stage0_data()
    
    # Stage 1
    df_stage1 = generate_stage1_data(df_stage0)
    
    # Stage 2
    df_stage2 = generate_stage2_data(df_stage1)
    
    # Stage 3
    res_stage3 = generate_stage3_data(df_stage2)
    if res_stage3:
        df_embeddings, vectorizer, svd = res_stage3
    else:
        return
    
    # Stage 4
    res_stage4 = generate_stage4_data(df_embeddings)
    if res_stage4:
        df_clusters, kmeans = res_stage4
    else:
        return
        
    # Stage 5
    df_topic_clusters = generate_stage5_data(df_stage2, df_clusters, vectorizer)
    
    # Stage 6
    df_topic_clusters = generate_stage6_data(df_stage2, df_clusters, df_topic_clusters)
    
    # Stage 7
    df_topic_clusters, df_fine_trends = generate_stage7_data(df_topic_clusters)
    
    # Stage 8
    df_topic_clusters = generate_stage8_data(df_embeddings, df_clusters, df_topic_clusters)
    
    # Stage 9
    df_fine_trends = generate_stage9_data(df_topic_clusters, df_fine_trends)
    
    # Stage 10
    df_topic_clusters, x_all = generate_stage10_data(df_topic_clusters)
    
    # Stage 11
    df_topic_clusters, rf = generate_stage11_data(df_stage2, df_clusters, df_topic_clusters)
    
    # Stage 12
    df_topic_clusters = generate_stage12_data(df_topic_clusters)
    
    # Stage 13
    df_topic_clusters, df_matrix = generate_stage13_data(df_topic_clusters)
    
    print(">>> 所有数据文件已生成至 realoutputs 文件夹。")

if __name__ == "__main__":
    main()
