import os
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.graphs import Neo4jGraph
from langchain.chains.graph_qa.cypher import GraphCypherQAChain
import streamlit as st


def main():
    st.set_page_config(
        layout="wide", page_title="Expert Finder v1", page_icon=":graph:"
    )
    #    st.sidebar.image('logo.png', use_column_width=True)
    with st.sidebar.expander("Expand Me"):
        st.markdown("""
    This application allows you to connect to a Neo4j graph database, and perform queries using natural language.
    It leverages LangChain and Anthropic's Claude model to generate Cypher queries that interact with the Neo4j database in real-time.
    """)
    st.title("DWS Expert Finder")

    load_dotenv()

    # Set QUERY API key
    if "QUERY_API_KEY" not in st.session_state:
        st.sidebar.subheader("Query Model Key")
        query_api_key = st.sidebar.text_input(
            "Enter your Query Model API Key:", type="password"
        )
        if query_api_key:
            os.environ["QUERY_API_KEY"] = query_api_key
            st.session_state["QUERY_API_KEY"] = query_api_key
            st.sidebar.success("Query API Key set successfully.")
            query_llm = ChatOpenAI(
                model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                base_url="https://us.aigw.galileo.roche.com/v1",
                api_key=query_api_key,
                temperature=0.0,
            )  # Use model that supports function calling
            st.session_state["query_llm"] = query_llm
    else:
        query_llm = st.session_state["query_llm"]

    # Initialize variables
    neo4j_url = None
    neo4j_username = None
    neo4j_password = None
    graph = None

    # Set Neo4j connection details
    if "neo4j_connected" not in st.session_state:
        st.sidebar.subheader("Connect to Neo4j Database")
        neo4j_url = st.sidebar.text_input(
            "Neo4j URL:", value="bolt://rkalvinpypoc.kau.roche.com:7687"
        )
        neo4j_username = st.sidebar.text_input("Neo4j Username:", value="user")
        neo4j_password = st.sidebar.text_input("Neo4j Password:", type="password")
        connect_button = st.sidebar.button("Connect")
        if connect_button and neo4j_password:
            try:
                graph = Neo4jGraph(
                    url=neo4j_url, username=neo4j_username, password=neo4j_password
                )
                st.session_state["graph"] = graph
                st.session_state["neo4j_connected"] = True
                # Store connection parameters for later use
                st.session_state["neo4j_url"] = neo4j_url
                st.session_state["neo4j_username"] = neo4j_username
                st.session_state["neo4j_password"] = neo4j_password
                st.sidebar.success("Connected to Neo4j database.")
            except Exception as e:
                st.error(f"Failed to connect to Neo4j: {e}")
    else:
        graph = st.session_state["graph"]
        neo4j_url = st.session_state["neo4j_url"]
        neo4j_username = st.session_state["neo4j_username"]
        neo4j_password = st.session_state["neo4j_password"]

    # Ensure that the Neo4j connection is established before proceeding
    if graph is not None:
        # Retrieve the graph schema
        schema = graph.get_schema

        # Set up the QA chain
        template = f"""
Instructions:
Use only relationship types and properties provided in schema.
Do not use other relationship types or properties that are not provided.
Do not limit your query results.
Use only data as your answer.

schema:
{schema}

Note:
Do not include explanations or apologies in your answers.
Do not answer questions that ask anything other than creating Cypher statements.
Do not include any text other than generated Cypher statements.



Question: {question}

Task: Generate a Cypher statement to query the graph database.
"""

        question_prompt = PromptTemplate(
            template=template, input_variables=["schema", "question"]
        )

        qa = GraphCypherQAChain.from_llm(
            llm=query_llm,
            graph=graph,
            cypher_prompt=question_prompt,
            verbose=True,
            allow_dangerous_requests=True,
        )
        st.session_state["qa"] = qa
    else:
        st.warning("Please connect to the Neo4j database")

    if "qa" in st.session_state:
        st.subheader("Ask a Question")
        with st.form(key="question_form"):
            question = st.text_input("Enter your question:")
            submit_button = st.form_submit_button(label="Submit")

        if submit_button and question:
            with st.spinner("Generating answer..."):
                res = st.session_state["qa"].invoke({"query": question})
                st.write("\n**Answer:**\n" + res["result"])


if __name__ == "__main__":
    main()
