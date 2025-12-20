suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(ggplot2)
  library(ggridges)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: Rscript cvm_entropy.R <input_tsv> <output_png> [width] [height] [dpi]")
}
input_tsv <- args[1]
output_png <- args[2]
width  <- ifelse(length(args) >= 3, as.numeric(args[3]), 8)
height <- ifelse(length(args) >= 4, as.numeric(args[4]), 5)
dpi    <- ifelse(length(args) >= 5, as.numeric(args[5]), 900)

cvm_results <- readr::read_tsv(input_tsv, show_col_types = FALSE) %>%
  mutate(
    model_category = case_when(
      grepl("fix", model, ignore.case = TRUE) & grepl("PMSF", model, ignore.case = TRUE) ~ "fix_PMSF",
      grepl("opt", model, ignore.case = TRUE) & grepl("PMSF", model, ignore.case = TRUE) ~ "opt_PMSF",
      grepl("fix", model, ignore.case = TRUE) ~ "fix_noPMSF",
      grepl("opt", model, ignore.case = TRUE) ~ "opt_noPMSF",
      TRUE ~ "other"
    )
  )

model_order <- cvm_results %>%
  group_by(model) %>%
  summarise(median_stat = median(W2_statistic, na.rm = TRUE), .groups = "drop") %>%
  arrange(median_stat) %>%
  pull(model)

cvm_results <- cvm_results %>%
  mutate(label = factor(model, levels = rev(model_order)))

color_palette <- c(
  "fix_noPMSF"  = "#9AC4DB",
  "opt_noPMSF"  = "#CB8D8B",
  "fix_PMSF"    = "#7BB661",
  "opt_PMSF"    = "#D4A373",
  "other"       = "grey70"
)

p_ridges <- ggplot(cvm_results, aes(x = W2_statistic, y = label, fill = model_category)) +
  geom_density_ridges(
    scale = 1.3, rel_min_height = 0, alpha = 0.7,
    color = "black", linewidth = 0.37,
    panel_scaling = FALSE, position = "identity"
  ) +
  scale_x_continuous(expand = c(0, 0), limits = c(0, NA)) +
  scale_y_discrete(expand = expansion(add = c(0.3, 0.3))) +
  scale_fill_manual(
    values = color_palette,
    labels = c(
      "fix_noPMSF"  = "fix (no PMSF)",
      "opt_noPMSF"  = "opt (no PMSF)",
      "fix_PMSF"    = "fix (PMSF)",
      "opt_PMSF"    = "opt (PMSF)",
      "other"       = "other"
    )
  ) +
  labs(x = expression(W^2 ~ "(Cramér-von Mises statistic) on sitewise entropy"), y = NULL) +
  theme_classic(base_size = 9) +
  theme(
    axis.title.x = element_text(size = 9),
    axis.text.x  = element_text(size = 8),
    axis.text.y  = element_text(size = 8),
    axis.ticks.y = element_line(linewidth = 0.4),
    axis.ticks.length.y = unit(2, "pt"),
    axis.line.x = element_line(linewidth = 0.5),
    axis.line.y = element_blank(),
    panel.grid.major.y = element_line(color = "grey85", linewidth = 0.3),
    panel.grid.major.x = element_blank(),
    legend.position = "top",
    legend.title = element_blank(),
    legend.text  = element_text(size = 7)
  )

ggsave(filename = output_png, plot = p_ridges, width = width, height = height, dpi = dpi)
cat(sprintf("Saved plot to: %s\n", output_png))