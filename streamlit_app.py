import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="DocBot", page_icon="📄", layout="wide")
st.title("📄 DocBot — PDF Question Answering")
st.caption("Powered by LangChain · FAISS · Ollama · sentence-transformers")

# ─────────────────────────────────────────
# Utility: Safe error handler
# ─────────────────────────────────────────
def get_error(resp):
    try:
        return resp.json().get("detail", "Unknown error")
    except:
        return resp.text


# ─────────────────────────────────────────
# Sidebar: Upload + Documents
# ─────────────────────────────────────────
with st.sidebar:
    st.header("Upload a PDF")
    uploaded_file = st.file_uploader("Choose a PDF", type="pdf")

    if uploaded_file:
        if st.button("Upload & Index", type="primary"):
            with st.spinner("Ingesting PDF... this may take a moment"):
                resp = requests.post(
                    f"{API_URL}/documents/upload",
                    files={
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            "application/pdf",
                        )
                    },
                )

            if resp.status_code == 200:
                data = resp.json()
                st.success(f"✅ Uploaded: {data['filename']}")
                st.rerun()
            else:
                st.error(f"Upload failed: {get_error(resp)}")

    st.divider()
    st.header("Your Documents")

    try:
        docs_resp = requests.get(f"{API_URL}/documents/")
        documents = docs_resp.json() if docs_resp.status_code == 200 else []
    except:
        documents = []

    if not documents:
        st.caption("No documents uploaded yet.")
        selected_doc = None
    else:
        doc_options = {
            f"{d['filename']} (ID: {d['id']})": d for d in documents
        }
        selected_label = st.selectbox("Select a document", list(doc_options.keys()))
        selected_doc = doc_options[selected_label]

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Pages", selected_doc["page_count"])
        with col2:
            size_kb = round(selected_doc["file_size"] / 1024, 1)
            st.metric("Size", f"{size_kb} KB")

        if st.button("🗑 Delete document", type="secondary"):
            resp = requests.delete(
                f"{API_URL}/documents/{selected_doc['id']}"
            )
            if resp.status_code == 200:
                st.success("Deleted successfully")
            else:
                st.error(get_error(resp))
            st.rerun()


# ─────────────────────────────────────────
# Main: Q&A Interface
# ─────────────────────────────────────────
if selected_doc:
    st.subheader(f"Ask a question about: {selected_doc['filename']}")

    question = st.text_input(
        "Your question",
        placeholder="What is this document about?"
    )
    top_k = st.slider(
        "Number of source chunks to retrieve",
        min_value=1,
        max_value=10,
        value=5
    )

    if st.button("Ask", type="primary") and question:
        with st.spinner("Thinking... (Ollama may take ~10s)"):
            resp = requests.post(
                f"{API_URL}/query/",
                json={
                    "document_id": selected_doc["id"],
                    "question": question,
                    "top_k": top_k,
                },
            )

        if resp.status_code == 200:
            data = resp.json()

            st.markdown("### Answer")
            st.markdown(data["answer"])

            with st.expander(
                f"📎 Source chunks ({len(data['sources'])} retrieved)"
            ):
                for i, src in enumerate(data["sources"], 1):
                    st.markdown(
                        f"**Chunk {i} — Page {src['page_number']}**"
                    )
                    st.caption(src["content"])
                    st.divider()
        else:
            st.error(f"Query failed: {get_error(resp)}")

    # ── Query History ─────────────────────
    st.divider()
    st.subheader("Query History")

    try:
        hist_resp = requests.get(
            f"{API_URL}/query/history/{selected_doc['id']}"
        )
        history = hist_resp.json() if hist_resp.status_code == 200 else []
    except:
        history = []

    if not history:
        st.caption("No queries yet for this document.")
    else:
        for log in history:
            with st.expander(f"Q: {log['question'][:80]}..."):
                st.markdown(f"**Answer:** {log['answer']}")
                st.caption(f"Asked at: {log['created_at']}")

else:
    st.info("👈 Upload a PDF from the sidebar to get started.")