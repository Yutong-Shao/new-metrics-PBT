
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
    weights = case_when(
      grepl("fix", model, ignore.case = TRUE) ~ "fix",
      grepl("opt", model, ignore.case = TRUE) ~ "opt",
      TRUE ~ "default"
    ),
    label_raw = model %>%
      gsub("fix", "", ., ignore.case = TRUE) %>%
      gsub("opt", "", ., ignore.case = TRUE) %>%
      trimws()
  ) %>%
  mutate(
    sort_group = case_when(
      weights == "default" ~ 1,
      weights == "fix"     ~ 2,
      weights == "opt"     ~ 3,
      TRUE ~ 4
    )
  ) %>%
  arrange(sort_group, label_raw) %>%
  mutate(label = factor(label_raw, levels = rev(unique(label_raw))))

p_ridges <- ggplot(cvm_results, aes(x = W2_statistic, y = label, fill = weights)) +
  geom_density_ridges(
    scale = 1.3, rel_min_height = 0, alpha = 0.7,
    color = "black", linewidth = 0.37,
    panel_scaling = FALSE, position = "identity"
  ) +
  scale_x_continuous(expand = c(0, 0)) +
  scale_y_discrete(expand = expansion(add = c(0.3, 0.3))) +
  scale_fill_manual(values = c("fix" = "#9AC4DB", "opt" = "#CB8D8B", "default" = "grey70")) +
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
