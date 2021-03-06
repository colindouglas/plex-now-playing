# Set working directory (ending with /) where it can save tokens, find credentials.
# NOTE: Password will be saved in plaintext in this folder! Choose somewhere secure.
wkdir <- "~/Scripts/"

# Set the path to the credentials and the auth token
credential_path <- paste0(wkdir, ".plex_creds")
token_path <- paste0(wkdir, ".plex_token")

# To automatically write the .plex_creds file, uncomment and modify the following lines 
# if (!(file.exists(credential_path))) {
#   write.table(data.frame("username" = "John_k_User", 
#                          "password" = "hunter2"),
#               file = paste0(wkdir, ".plex_creds"), 
#               col.names = FALSE, row.names = FALSE, sep = ",")
# }
# The above lines can be commented out after the first run

# Load the necessary packages
packages <- c("dplyr", "tibble", "httr", "readr", "tidyr", "stringr")
if (!all(unlist(lapply(packages, require, character.only = TRUE)))) {
  install.packages(packages)
  lapply(packages, require, character.only = TRUE)
}

# Check if there's a token written and read it in
if (file.exists(token_path)) {
  token <- read_csv(token_path)
} else {
  token <- NULL
}

# If there's no token or the token is more than a day old, re-auth with plex.tv and get a new token
if (!length(token) | token$authed_at < Sys.Date()) {
  credentials <- read_csv(credential_path, col_names = FALSE)
  
  token_response <- content(
    POST(
      url = "https://plex.tv/users/sign_in.json", 
      body = paste0("user%5Blogin%5D=", credentials[[1]], "&user%5Bpassword%5D=", credentials[[2]]), 
      add_headers("X-Plex-Client-Identifier" = "NowPlayingScript", 
                  "X-Plex-Product" = "NowPlayingScript",
                  "X-Plex-Version" = "0.0.1")
    )
  )
  
  if (length(token_response$error)) {
    cat("Error getting authentication token! Check Plex credentials")
    quit(status = 1)
  }

  token <- token_response %>% 
    tibble(object = .) %>% 
    unnest_wider(object) %>%
    select(-subscription, -roles) %>% 
    add_column(authed_at = Sys.Date())
  
  write_csv(token, path = token_path) 
  
}

token <- token$authToken

# Get data on the current streams from the local Plex server
now_playing <- content(GET("http://127.0.0.1:32400/status/sessions", add_headers("X-Plex-Token" = token)))

# Check if something is playing, and if it is, print some data about the streams
if (!is.null(now_playing$MediaContainer$Metadata)) {
  np_nested <- tibble(metadata = now_playing$MediaContainer$Metadata) %>%
    unnest_wider(metadata) %>%
    unnest_wider(User, names_sep = ".")
  
  # If there's no "last viewed at" time, use the current time
  if (is.null(np_nested$lastViewedAt)) np_nested$lastViewedAt <- as.numeric(Sys.time())
  
  current <- np_nested %>%
    rowwise() %>%
    mutate(episode = paste0("S", gsub("[A-Za-z ]+", "", parentTitle), "E", str_pad(index, 2, pad = "0"))) %>%
    select(user = User.title,
           series = grandparentTitle,
           ep_name = title,
           time = lastViewedAt,
           episode)
  
  print_pretty <- function(df, row) {
    time <- as.numeric(df$time[row]) %>% 
      as.POSIXct(origin = "1970-01-01", tz = Sys.timezone()) %>% 
      format("%b %d, %I:%M%P")
    paste0(time, ": ", 
           substr(df$user[row], start = 1, stop = 12), " // ", 
           substr(df$series[row], start = 1, stop = 20), " - ", 
           substr(df$episode[row], start = 1, stop = 20), " - ", 
           substr(df$ep_name[row], start = 1, stop = 20)
    )
  }
  
  for (i in 1:nrow(current)) {
    cat(print_pretty(current, i))
    cat("\n")
  }
} else {
  cat("Nothing playing")
}
