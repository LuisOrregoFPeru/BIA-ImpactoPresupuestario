import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import matplotlib.ticker as mticker
import math

st.set_page_config(page_title="BIA • Impacto Presupuestario", layout="wide")
st.title("2️⃣ BIA • Impacto Presupuestario")

def descarga_csv(df: pd.DataFrame, nombre: str):
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Descargar CSV", csv, file_name=f"{nombre}.csv", mime="text/csv")

st.header("2️⃣ Impacto Presupuestario (BIA)")

costo_actual = st.number_input("Costo intervención actual (U.M.)", min_value=0.0, step=1.0)
costo_nueva  = st.number_input("Costo intervención nueva (U.M.)",  min_value=0.0, step=1.0)
delta = costo_nueva - costo_actual
st.write(f"**Δ Costo por caso tratado:** U.M. {delta:,.2f}")

metodo = st.radio(
    "Definir población objetivo por:",
    ("Prevalencia (%) y población total", "Casos anuales referidos")
)
if metodo == "Prevalencia (%) y población total":
    pop_total   = st.number_input("Población total", min_value=1, step=1)
    prevalencia = st.number_input(
        "Prevalencia (%)", 
        min_value=0.0, max_value=100.0, value=100.0, step=0.1
    )
    casos_anio = int(pop_total * prevalencia / 100.0)
    st.write(f"Casos/año estimados: {casos_anio:,d} ({prevalencia:.1f}% de {pop_total:,d})")
else:
    casos_anio = st.number_input("Número de casos anuales", min_value=0, step=1)
    st.write(f"Casos por año: {casos_anio:,d}")

yrs = st.number_input("Horizonte (años)", 1, step=1)

st.subheader("PIM histórico (últimos 5 años)")
pim_hist = []
for i in range(5):
    offset = 4 - i
    label = f"-{offset}" if offset > 0 else "actual"
    val = st.number_input(
        f"PIM año {label}",
        min_value=0.0,
        step=1.0,
        key=f"pim_hist_{i}"
    )
    pim_hist.append(val)

growth_rates = []
for i in range(1, 5):
    prev = pim_hist[i-1]
    curr = pim_hist[i]
    rate = (curr - prev) / prev if prev > 0 else 0.0
    growth_rates.append(rate)
avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0.0
avg_growth = round(avg_growth, 3)
st.write(f"**Tasa media anual de crecimiento PIM:** {avg_growth:.1%}")

uptake_list = []
for i in range(int(yrs)):
    label = "actual" if i == 0 else f"+{i}"
    pct = st.slider(
        f"Introducción año {label} (%)",
        0, 100, 100, 1,
        key=f"uptake_{i}"
    )
    uptake_list.append(pct)

uso_nueva  = [math.ceil(casos_anio * pct/100) for pct in uptake_list]
uso_actual = [casos_anio - un for un in uso_nueva]
cost_inc   = [delta * un for un in uso_nueva]
acumulado  = np.cumsum(cost_inc)

last_pim = pim_hist[-1]
pim_proj = []
for i, ci in enumerate(cost_inc):
    if i == 0:
        pim_i = last_pim + ci
    else:
        pim_i = pim_proj[i-1] * (1 + avg_growth) + ci
    pim_proj.append(pim_i)

df = pd.DataFrame({
    "Año":                    [f"Año {i+1}" for i in range(int(yrs))],
    "Casos intervención actual": uso_actual,
    "Casos intervención nueva":  uso_nueva,
    "Costo incremental":      cost_inc,
    "Acumulado Costo Incremental":              acumulado,
    "PIM proyectado":         pim_proj,
    "Impacto en PIM":         [
        ac/pp if pp>0 else np.nan
        for ac, pp in zip(acumulado, pim_proj)
    ]
})

df_disp = df.loc[:, [
    "Año",
    "Casos intervención actual",
    "Casos intervención nueva",
    "Costo incremental",
    "Acumulado Costo Incremental",
    "PIM proyectado",
    "Impacto en PIM"
]].copy()

df_disp["Casos intervención actual"] = df_disp["Casos intervención actual"].map("{:,.0f}".format)
df_disp["Casos intervención nueva"]  = df_disp["Casos intervención nueva"].map("{:,.0f}".format)
df_disp["Costo incremental"]         = df_disp["Costo incremental"].map("{:,.2f}".format)
df_disp["Acumulado Costo Incremental"]  = df_disp["Acumulado Costo Incremental"].map("{:,.2f}".format)
df_disp["PIM proyectado"]            = df_disp["PIM proyectado"].map("{:,.2f}".format)
df_disp["Impacto en PIM"]            = df_disp["Impacto en PIM"].map("{:.2%}".format)

st.dataframe(
    df_disp.style
           .set_properties(**{"text-align": "center"})
           .set_table_styles([{"selector": "th", "props": [("text-align", "center")]}]),
    use_container_width=True
)

st.markdown("---")
st.caption("""
**Nota:**  
- Casos intervención actual = Casos/año – Casos intervención nueva  
- Casos intervención nueva = Casos/año × % introducción  
- Costo incremental = Δ costo por caso × Casos intervención nueva  
- Acumulado Costo incremental = suma de todos los Costos incrementales hasta el año t  
- PIM proyectado Año 0 = PIM histórico + Costo incremental Año 0  
- PIM proyectado Año t ≥ 1 = (PIM proyectado del año anterior × (1 + tasa media anual de crecimiento PIM)) + Costo incremental Año t  
- Impacto en PIM = Acumulado / PIM proyectado (expresado en %)  
""")

st.success(f"Acumulado en {yrs} años: U.M. {acumulado[-1]:,.2f}")
st.info(f"Impacto relativo final en PIM: {df['Impacto en PIM'].iloc[-1]:.2%}")

fig1, ax1 = plt.subplots()
ax1.plot(df["Año"], df["Casos intervención actual"], marker="o", label="Casos actual")
ax1.plot(df["Año"], df["Casos intervención nueva"], marker="o", linestyle="--", label="Casos nuevos")

ax1.set_xlabel("Año")
ax1.set_ylabel("Número de casos")
ax1.set_title("Tendencia de Casos")
ax1.legend()

ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
st.pyplot(fig1)

fig2, ax2 = plt.subplots()
ax2.plot(df["Año"], df["Costo incremental"], marker="o", label="Costo incremental")
ax2.plot(df["Año"], df["Acumulado Costo Incremental"],        marker="o", label="Costo acumulado")

ax2.set_xlabel("Año")
ax2.set_ylabel("Costo (U.M.)")
ax2.set_title("Tendencia de Costos")
ax2.legend()

ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.2f}"))
st.pyplot(fig2)

descarga_csv(df, "BIA_resultados")
