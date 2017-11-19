using Newtonsoft.Json.Linq;
using System.Collections.Generic;

namespace magenta.Models
{
    public class HashItem
    {
        public string Key { get; set; }
    }

    public class SocialAccount
    {
        public string Provider { get; set; }
        public string Pid { get; set; }
        public JObject Info { get; set; }
        public JObject Credentials { get; set; }
        public int Errors { get; set; }
        public JArray PostedSet { get; set; }
        public JArray MessageMap { get; set; }
        public long LastPublish { get; set; }
    }

    public class RootAccount
    {
        public SocialAccount Account { get; set; }
        public Dictionary<string, SocialAccount> Accounts { get; set; }
        public Dictionary<string, Link> Links { get; set; }
        public Dictionary<string, LogItem> Logs { get; set; }
    }

    public class Link
    {
        public SocialAccount Source { get; set; }
        public SocialAccount Target { get; set; }
        public JObject Filters { get; set; }
        public JObject Options { get; set; }
        public Schedule Schedule { get; set; }
        public long BoundStamp { get; set; }
        public long UpdatedStamp { get; set; }
    }

    public class LogItem
    {
        public JArray Messages { get; set; }
    }

    public class Schedule
    {
        public bool Enabled { get; set; }
        public JObject Days { get; set; }
    }
}
