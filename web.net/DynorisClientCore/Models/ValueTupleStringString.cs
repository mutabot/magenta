// <auto-generated>
// Code generated by Microsoft (R) AutoRest Code Generator.
// Changes may cause incorrect behavior and will be lost if the code is
// regenerated.
// </auto-generated>

namespace DynorisClient.Models
{
    using Newtonsoft.Json;
    using System.Linq;

    public partial class ValueTupleStringString
    {
        /// <summary>
        /// Initializes a new instance of the ValueTupleStringString class.
        /// </summary>
        public ValueTupleStringString()
        {
            CustomInit();
        }

        /// <summary>
        /// Initializes a new instance of the ValueTupleStringString class.
        /// </summary>
        public ValueTupleStringString(string item1 = default(string), string item2 = default(string))
        {
            Item1 = item1;
            Item2 = item2;
            CustomInit();
        }

        /// <summary>
        /// An initialization method that performs custom operations like setting defaults
        /// </summary>
        partial void CustomInit();

        /// <summary>
        /// </summary>
        [JsonProperty(PropertyName = "item1")]
        public string Item1 { get; set; }

        /// <summary>
        /// </summary>
        [JsonProperty(PropertyName = "item2")]
        public string Item2 { get; set; }

    }
}